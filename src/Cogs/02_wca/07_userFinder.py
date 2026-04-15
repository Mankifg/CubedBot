import discord
from discord.ext import commands, tasks
import requests

from datetime import datetime as dt
import datetime
from datetime import timedelta
import time
import asyncio

import src.db as db
from src.hardstorage import * 

import src.wca_function as wca_function
from src.guild_access import both_guild_ids

COMP_URL = "https://www.worldcubeassociation.org/competitions/{}"
REGISTERED_URL = "https://www.worldcubeassociation.org/api/v1/competitions/{}/registrations"
NUMBER_OF_DAYS_TO_SEARCH = 7
URL_FOR_REGIONS = "https://www.worldcubeassociation.org/api/v0/countries"

def _load_regions():
    try:
        resp = requests.get(URL_FOR_REGIONS, timeout=8)
        resp.raise_for_status()
        raw_regions = resp.json()
        if isinstance(raw_regions, dict):
            raw_regions = raw_regions.get("items", [])
        if isinstance(raw_regions, list):
            return raw_regions
    except requests.RequestException as exc:
        print(f"[WARN] regions fetch failed: {exc}; using local country fallback")

    fallback = []
    for iso2, name in getattr(wca_function, "COUNTRIES_DICT", {}).items():
        if isinstance(iso2, str) and isinstance(name, str):
            fallback.append({"iso2": iso2, "name": name})
    return fallback

raw_regions = _load_regions()

REGIONS = []
ISO2 = []
for elem in raw_regions:
    if not isinstance(elem, dict):
        continue
    iso2 = elem.get("iso2Code") or elem.get("iso2")
    name = elem.get("name")
    if not isinstance(iso2, str) or not isinstance(name, str):
        continue
    ISO2.append(iso2.lower())
    REGIONS.append(f"{iso2.lower()} - {name}")

print(ISO2)

COUNTRY_NAMES = {}
for elem in raw_regions:
    if not isinstance(elem, dict):
        continue
    iso2 = elem.get("iso2Code") or elem.get("iso2")
    name = elem.get("name")
    if isinstance(iso2, str) and isinstance(name, str):
        COUNTRY_NAMES[iso2.lower()] = name

def convert_to_abbreviated_form(full_name):
    print(full_name)
    name_parts = full_name.strip().split()
    if len(name_parts) < 2:
        raise ValueError("Full name must include at least a first name and a surname.")
    first_names_and_middle = name_parts[:-1]
    last_surname = name_parts[-1]
    abbreviated_names = [name[0].upper() + '.' for name in first_names_and_middle]
    return " ".join(abbreviated_names + [last_surname.capitalize()])


def max_len_in_collum(data):
    return [max(len(str(element)) for element in column) for column in zip(*data)]

def valid_time(time):
    if time is None:
        return False
    try:
        dt.strptime(time, '%Y-%m-%d')
    except ValueError:
        return False
    
    return True

def _sl_count_form(count):
    last_two = count % 100
    if last_two == 1:
        return "one"
    if last_two == 2:
        return "two"
    if last_two in (3, 4):
        return "few"
    return "many"


def _number_text(language, count):
    if count >= 10:
        return str(count)
    if language == "sl":
        return {
            1: "En",
            2: "Dva",
            3: "Trije",
            4: "Štirje",
            5: "Pet",
            6: "Šest",
            7: "Sedem",
            8: "Osem",
            9: "Devet",
        }.get(count, str(count))
    return {
        1: "One",
        2: "Two",
        3: "Three",
        4: "Four",
        5: "Five",
        6: "Six",
        7: "Seven",
        8: "Eight",
        9: "Nine",
    }.get(count, str(count))


def _localize_competitor_label(language, count):
    if language == "sl":
        form = _sl_count_form(count)
        if form == "one":
            return "tekmovalec"
        if form == "two":
            return "tekmovalca"
        if form == "few":
            return "tekmovalci"
        return "tekmovalcev"
    return "competitor" if count == 1 else "competitors"


def _localize_competitions_label(language, count):
    if language == "sl":
        form = _sl_count_form(count)
        if form == "one":
            return "tekmovanje"
        if form == "two":
            return "tekmovanji"
        if form == "few":
            return "tekmovanja"
        return "tekmovanj"
    return "competition" if count == 1 else "competitions"

def _weekly_copy(language, country_code):
    country_name = COUNTRY_NAMES.get(country_code.lower(), country_code.upper())
    if language == "sl":
        return {
            "title": "Iskalec tekmovanj",
            "period": "Obdobje",
            "competitions": f"Tekmovanja, kjer so prijavljeni tekmovalci regije: {country_code.title()} - {country_name}",
            "stats": "Statistika",
            "stats_value": lambda competitions_count, elapsed: f"Skenirano: {_number_text('sl', competitions_count)} {_localize_competitions_label('sl', competitions_count)}. Čas: {elapsed} sec",
            "empty": "Ni rezultatov.",
            "part": lambda idx: f"{idx}. del",
        }
    return {
        "title": "Competition Finder",
        "period": "Period",
        "competitions": f"Competitions with registered competitors from: {country_code.upper()} - {country_name}",
        "stats": "Statistics",
        "stats_value": lambda competitions_count, elapsed: f"Scanned: {_number_text('en', competitions_count)} {_localize_competitions_label('en', competitions_count)}. Time: {elapsed} sec",
        "empty": "No results.",
        "part": lambda idx: f"Part {idx}",
    }

def _load_weekly_targets():
    row = db.load_second_table_idd(7)
    data = row.get("data")
    if not isinstance(data, dict):
        return []

    if isinstance(data.get("userfinder_channel"), str):
        return [{
            "key": "si",
            "channel": data["userfinder_channel"],
            "country": "SI",
            "language": "sl",
        }]

    targets = data.get("userfinder_targets")
    if not isinstance(targets, list):
        return []
    return [target for target in targets if isinstance(target, dict)]


def _build_userfinder_item(competition_name, competition_id, matching_competitors, language):
    plural = _localize_competitor_label(language, matching_competitors)
    return f"* [{competition_name}]({COMP_URL.format(competition_id)})\n  • {_number_text(language, matching_competitors)} {plural}\n"


class userfinderCog(commands.Cog, name="userfinder command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self._last_weekly_run = None
        self.weekly_userfinder.start()

    def _resolve_manual_language(self, guild_id):
        if guild_id is None:
            return "sl"

        for target in _load_weekly_targets():
            channel = target.get("channel")
            try:
                channel = int(channel)
            except (TypeError, ValueError):
                continue

            target_channel = self.bot.get_channel(channel)
            if target_channel is None or target_channel.guild is None:
                continue

            if target_channel.guild.id == guild_id:
                return str(target.get("language", "sl")).lower().strip() or "sl"

        return "sl"

    async def _build_userfinder_sections(self, nat, start_date, end_date, language="sl"):
        all_competitions = wca_function.list_of_events_from(start_date, end_date)
        print(len(all_competitions), all_competitions)

        s_time = time.time()
        atLeastOneComp = False
        fetch_failures = 0
        send_obj = []
        send_single = ""

        for competition_id in all_competitions:
            print("trying:", competition_id, end=" ")

            resp = None
            for _ in range(4):
                try:
                    resp = await asyncio.to_thread(
                        requests.get,
                        REGISTERED_URL.format(competition_id),
                        timeout=4,
                    )
                    print("trying ", resp.status_code)
                    if resp.status_code == 200:
                        break
                except requests.RequestException:
                    print("req timeout", competition_id)
                    resp = None

            if resp is None or resp.status_code != 200:
                fetch_failures += 1
                continue

            print(resp.status_code)
            try:
                resp = resp.json()
            except ValueError:
                fetch_failures += 1
                continue

            matching_competitors = 0
            for user in resp:
                iso2_code = user["user"]["country_iso2"]
                if iso2_code.lower() == nat.lower():
                    matching_competitors += 1

            if matching_competitors > 0:
                atLeastOneComp = True
                success, comp_data = await asyncio.to_thread(wca_function.get_comp_data, competition_id)
                competition_name = competition_id
                if success:
                    competition_name = comp_data.get("name", competition_id)

                to_add = _build_userfinder_item(
                    competition_name,
                    competition_id,
                    matching_competitors,
                    language,
                )
                if len(send_single) + len(to_add) > 1024:
                    send_obj.append(send_single)
                    send_single = to_add
                else:
                    send_single += to_add

        if send_single != "":
            send_obj.append(send_single)
        if not atLeastOneComp:
            send_obj = ["Ni rezultatov."]

        elapsed = int(round(time.time() - s_time))
        return all_competitions, send_obj, elapsed

    async def _scan_weekly_targets(self, targets, start_date, end_date):
        all_competitions = wca_function.list_of_events_from(start_date, end_date)
        print(len(all_competitions), all_competitions)

        target_meta = {}
        for target in targets:
            target_key = str(target.get("key", "")).strip()
            country = str(target.get("country", "")).lower().strip()
            language = str(target.get("language", "en")).lower().strip() or "en"
            if not target_key or not country:
                continue
            target_meta[target_key] = {
                "country": country,
                "language": language,
                "items": [],
            }

        s_time = time.time()
        comp_name_cache = {}

        for competition_id in all_competitions:
            print("trying:", competition_id, end=" ")

            resp = None
            for _ in range(4):
                try:
                    resp = await asyncio.to_thread(
                        requests.get,
                        REGISTERED_URL.format(competition_id),
                        timeout=4,
                    )
                    print("trying ", resp.status_code)
                    if resp.status_code == 200:
                        break
                except requests.RequestException:
                    print("req timeout", competition_id)
                    resp = None

            if resp is None or resp.status_code != 200:
                continue

            try:
                registrations = resp.json()
            except ValueError:
                continue

            counts = {key: 0 for key in target_meta.keys()}
            for user in registrations:
                iso2_code = str(user["user"]["country_iso2"]).lower()
                for target_key, meta in target_meta.items():
                    if iso2_code == meta["country"]:
                        counts[target_key] += 1

            matched_keys = [key for key, value in counts.items() if value > 0]
            if not matched_keys:
                continue

            if competition_id not in comp_name_cache:
                success, comp_data = await asyncio.to_thread(wca_function.get_comp_data, competition_id)
                comp_name_cache[competition_id] = comp_data.get("name", competition_id) if success else competition_id

            competition_name = comp_name_cache[competition_id]
            for target_key in matched_keys:
                count = counts[target_key]
                language = target_meta[target_key]["language"]
                plural = _localize_competitor_label(language, count)
                target_meta[target_key]["items"].append(
                    f"* [{competition_name}]({COMP_URL.format(competition_id)})\n  • {count} {plural}\n"
                )

        elapsed = int(round(time.time() - s_time))
        return all_competitions, target_meta, elapsed

    def _chunk_weekly_items(self, items, empty_text):
        send_obj = []
        send_single = ""
        for item in items:
            if len(send_single) + len(item) > 1024:
                send_obj.append(send_single)
                send_single = item
            else:
                send_single += item
        if send_single:
            send_obj.append(send_single)
        if not send_obj:
            send_obj = [empty_text]
        return send_obj

    async def _send_weekly_target(self, target, all_competitions, target_meta, elapsed, start_date, end_date):
        target_key = str(target.get("key", "")).strip()
        if not target_key or target_key not in target_meta:
            return

        channel = target.get("channel")
        try:
            channel = int(channel)
        except (TypeError, ValueError):
            print(f"[ERROR] invalid userfinder target channel for {target_key}: {channel}")
            return

        ch = self.bot.get_channel(channel)
        if ch is None:
            print(f"[ERROR] userfinder_channel not found for {target_key}: {channel}")
            return

        country = target_meta[target_key]["country"]
        language = target_meta[target_key]["language"]
        copy = _weekly_copy(language, country)
        send_obj = self._chunk_weekly_items(target_meta[target_key]["items"], copy["empty"])

        q = discord.Embed(title=copy["title"])
        q.add_field(
            name=copy["period"],
            value=f"<t:{int(start_date.timestamp())}:D> - <t:{int(end_date.timestamp())}:D>",
        )
        first_send = await ch.send(embed=q)

        q.add_field(
            name=copy["competitions"],
            value=send_obj[0],
            inline=False,
        )
        q.add_field(
            name=copy["stats"],
            value=copy["stats_value"](len(all_competitions), elapsed),
        )
        await first_send.edit(embed=q)

        if len(send_obj) > 1:
            for i in range(1, len(send_obj)):
                part = discord.Embed(title=copy["part"](i + 1))
                part.add_field(name=".", value=send_obj[i])
                await ch.send(embed=part)

    @tasks.loop(time=datetime.time(hour=16, minute=0, tzinfo=datetime.timezone.utc))
    async def weekly_userfinder(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if now_utc.weekday() != 2:  # Wednesday
            return

        run_key = (now_utc.year, now_utc.isocalendar().week)
        if self._last_weekly_run == run_key:
            return

        start_date = dt.now()
        end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)
        targets = _load_weekly_targets()
        if not targets:
            print("[WARN] no userfinder targets configured")
            return

        all_competitions, target_meta, elapsed = await self._scan_weekly_targets(targets, start_date, end_date)
        for target in targets:
            await self._send_weekly_target(target, all_competitions, target_meta, elapsed, start_date, end_date)

        self._last_weekly_run = run_key

    @weekly_userfinder.before_loop
    async def before_weekly_userfinder(self):
        await self.bot.wait_until_ready()
    async def get_regions(ctx: discord.AutocompleteContext):
        return REGIONS        
    
    @discord.command(
        name="userfinder",
        usage="(nationality) [start date: YYYY-MM-DD] [end date: YYYY-MM-DD]",
        description="Given nationality and time frame finds competitors who are competing",
        guild_ids=both_guild_ids(),
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def userFinder(
        self, ctx: discord.ApplicationContext,
        nationality: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_regions)), # type: ignore
        #   test: discord.Option(Attachment), # type: ignore
        user_start_date:str=None,
        end_date:str=None,
        ):
        
        nat = nationality.split("-")[0].strip()
        if nat not in ISO2:
            print(nat)
            language = self._resolve_manual_language(ctx.guild_id)
            if language == "sl":
                error = discord.Embed(title="Region should be picked from one of the provided ones",
                                  description="Izbrati je potrebo eno izmed regij iz seznama.",
                                  color=discord.Colour.red())
            else:
                error = discord.Embed(title="Region should be picked from one of the provided ones",
                                  description="Please select one of the provided regions from the list.",
                                  color=discord.Colour.red())
            await ctx.respond(embed=error)
            return
        language = self._resolve_manual_language(ctx.guild_id)
        await ctx.defer()
        
        start_date = dt.now()
        if valid_time(user_start_date):
            start_date = dt.strptime(user_start_date, '%Y-%m-%d')
            
        if end_date is None:
            end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)  
        elif end_date.isnumeric():
            end_date = start_date + timedelta(days=int(end_date))
        elif not valid_time(end_date):
            end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)
        else:
            end_date = dt.strptime(end_date, '%Y-%m-%d')

        all_competitions, send_obj, elapsed = await self._build_userfinder_sections(nat, start_date, end_date, language=language)
        copy = _weekly_copy(language, nat)
        
        q = discord.Embed(title=copy["title"])
        q.add_field(name=copy["period"],
                    value=f"<t:{int(start_date.timestamp())}:D> - <t:{int(end_date.timestamp())}:D>")
        q.add_field(name=copy["competitions"], value=send_obj[0], inline=False)
        q.add_field(
            name=copy["stats"],
            value=copy["stats_value"](len(all_competitions), elapsed),
        )
        print("ready to send")
        await ctx.respond(embed=q)
        print("send")
        
        if (len(send_obj) > 1):
            for i in range(1,len(send_obj)):
                send_single = send_obj[i]
                
                q = discord.Embed(title=copy["part"](i + 1))
                q.add_field(name=".",value=send_single)
                await ctx.send(embed=q)

            
    
def setup(bot: commands.Bot):
    bot.add_cog(userfinderCog(bot))
