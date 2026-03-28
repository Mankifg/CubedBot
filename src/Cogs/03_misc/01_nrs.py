import discord
from discord.ext import commands
import requests

from discord.ext import tasks
from datetime import datetime as dt

import src.wca_function as wca_function
import src.db as db
import src.functions as functions

# Static WCA Europe ISO2 list (sourced from /api/v0/countries on 2026-03-17).
EUROPEAN_ISO2 = {
    "AD","AL","AM","AT","AZ","BA","BE","BG","BY","CH","CY","CZ","DE","DK","EE","ES","FI","FR","GB","GE","GR","HR","HU","IE","IL","IS","IT","LI","LT","LU","LV","MC","MD","ME","MK","MT","NL","NO","PL","PT","RO","RS","RU","SE","SI","SK","SM","TR","UA","VA","XE","XK",
}
MEAN_EVENT_IDS = {"444bf", "555bf", "333fm", "666", "777"}

def _person_country_iso2(record):
    person = record.get("result", {}).get("person", {})
    return str(person.get("country", {}).get("iso2", "")).upper()

def _record_tag(record):
    return str(record.get("tag", "")).upper()

def should_post_record(record):
    tag = _record_tag(record)
    country_iso2 = _person_country_iso2(record)
    if country_iso2 == "SI" or tag == "WR":
        return True
    if tag == "CR":
        return country_iso2 in EUROPEAN_ISO2
    return False

def target_should_post_record(record, target):
    tag = _record_tag(record)
    country_iso2 = _person_country_iso2(record)
    countries = {
        str(country).upper()
        for country in target.get("countries", [])
        if isinstance(country, str)
    }

    if tag == "NR" and country_iso2 in countries:
        return True
    if tag == "WR" and bool(target.get("include_wr")):
        return True
    if tag == "CR" and bool(target.get("include_er")) and country_iso2 in EUROPEAN_ISO2:
        return True
    return False

def display_tag(record):
    tag = str(record.get("tag", "")).upper()
    country_iso2 = str(record.get("result", {}).get("person", {}).get("country", {}).get("iso2", "")).upper()
    if tag == "CR" and country_iso2 in EUROPEAN_ISO2:
        return "ER"
    return tag

def display_record_type(record_type, event_id):
    if record_type == "average" and event_id in MEAN_EVENT_IDS:
        return "mean"
    return record_type

def load_nr_targets():
    row = db.load_second_table_idd(3)
    data = row.get("data")
    if not isinstance(data, dict):
        return []

    # Backward-compatible fallback for the old single-target layout.
    if isinstance(data.get("records_channel"), str):
        return [{
            "key": "si",
            "channel": data["records_channel"],
            "countries": ["SI"],
            "include_wr": True,
            "include_er": True,
        }]

    targets = data.get("records_targets")
    if not isinstance(targets, list):
        return []
    return [target for target in targets if isinstance(target, dict)]

def load_nr_dedupe_row():
    return db.load_second_table_idd(4)

def ensure_dedupe_map(row, target_keys):
    if not isinstance(row.get("data"), dict):
        row["data"] = {}

    dedupe = row["data"].get("records_dedupe")

    # Backward-compatible fallback for the old single list layout.
    if isinstance(dedupe, list):
        row["data"]["records_dedupe"] = {"si": dedupe}
        dedupe = row["data"]["records_dedupe"]

    if not isinstance(dedupe, dict):
        dedupe = {}
        row["data"]["records_dedupe"] = dedupe

    for key in target_keys:
        existing = dedupe.get(key)
        if not isinstance(existing, list):
            dedupe[key] = []

    return dedupe

def already_sent_nr(dedupe_map, target_key, nr):
    print("chekcing nr", target_key, nr)
    already_sent = dedupe_map.get(target_key, [])
    print(nr in already_sent)
    return nr in already_sent

def mark_sent_nr(dedupe_map, target_key, nr):
    already_sent = dedupe_map.setdefault(target_key, [])
    if nr not in already_sent:
        print("ins", target_key, nr)
        already_sent.append(nr)

def build_record_embed(record):
    show_tag = display_tag(record)
    person = record["result"]["person"]
    round_obj = record["result"]["round"]
    event_id = round_obj["competitionEvent"]["event"]["id"]
    shown_type = display_record_type(record["type"], event_id)
    titl = f"{show_tag} {shown_type}"

    if show_tag == "NR":
        q = discord.Embed(title=titl, color=discord.Colour.green())
    elif show_tag == "ER":
        q = discord.Embed(title=titl, color=discord.Colour.yellow())
    else:
        q = discord.Embed(title=titl, color=discord.Colour.red())

    q.add_field(
        name=f':flag_{person["country"]["iso2"].lower()}: {person["name"]}',
        value=f'[{person["wcaId"]}](https://www.worldcubeassociation.org/persons/{person["wcaId"]})',
    )

    q.add_field(
        name=f'{round_obj["competitionEvent"]["event"]["name"]}',
        value=f'{round_obj["competitionEvent"]["competition"]["name"]}',
        inline=False,
    )

    times = []
    for el in record["result"]["attempts"]:
        times.append(el["result"])

    if shown_type == "mean":
        result_label = "MEAN"
    elif record["type"] == "average":
        result_label = "AVERAGE"
    else:
        result_label = "SINGLE"

    result_value = functions.convert_to_human_frm(record["attemptResult"], event_id)
    solves_value = functions.arry_to_human_frm(times, event_id)
    event_name = round_obj["competitionEvent"]["event"]["name"]
    comp_name = round_obj["competitionEvent"]["competition"]["name"]
    q.set_field_at(
        1,
        name=event_name,
        value=(
            f"{comp_name}\n"
            f"\n"
            f"**{result_label}:** `{result_value}`\n"
            f"SOLVES: {solves_value}"
        ),
        inline=False,
    )

    if show_tag == "NR":
        q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/nr.png")
    elif show_tag == "ER":
        q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/cr.png")
    elif show_tag == "WR":
        q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/wr.png")
    else:
        print("[ERROR] not nr,er or wr?")

    return q

class nrCog(commands.Cog, name="nr command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.wca_live_check.start()


    @tasks.loop(seconds=300)
    async def wca_live_check(self):
        targets = load_nr_targets()
        if not targets:
            print("[WARN] no records targets configured")
            return

        dedupe_row = load_nr_dedupe_row()
        target_keys = [
            str(target.get("key", "")).strip()
            for target in targets
            if str(target.get("key", "")).strip()
        ]
        dedupe_map = ensure_dedupe_map(dedupe_row, target_keys)

        print(f"[INFO] wca live record check ({', '.join(target_keys)})")
        resp = requests.post(
            url="https://live.worldcubeassociation.org/api/graphql",
            json={
                "query": """
                query {
                    recentRecords {
                    id
                    type
                    tag
                    attemptResult
                    result {
                        attempts {
                        result
                        }
                        person {
                        name
                        wcaId
                        country {
                            iso2
                            name
                        }
                        }
                        round {
                        id
                        competitionEvent {
                            event {
                            id
                            name
                            }
                            competition {
                            id
                            name
                            }
                        }
                        }
                    }
                    }
                }
                """
            },
        ).json()["data"]["recentRecords"]
        
      
        print(len(resp))

        dirty_dedupe = False
        for record in resp:
            print(record["id"])
            q = None

            for target in targets:
                target_key = str(target.get("key", "")).strip()
                if not target_key:
                    continue
                if not target_should_post_record(record, target):
                    continue
                if already_sent_nr(dedupe_map, target_key, record["id"]):
                    continue

                if q is None:
                    print("RECORD FOUND !!!", record)
                    q = build_record_embed(record)

                channel = target.get("channel")
                try:
                    channel = int(channel)
                except (TypeError, ValueError):
                    print(f"[ERROR] invalid records target channel for {target_key}: {channel}")
                    continue

                ch = self.bot.get_channel(channel)
                if ch is None:
                    print(f"[ERROR] records_channel not found for {target_key}: {channel}")
                    continue

                await ch.send(embed=q)
                mark_sent_nr(dedupe_map, target_key, record["id"])
                dirty_dedupe = True
                print("sent", target_key)

        if dirty_dedupe:
            db.save_second_table_idd(dedupe_row)
                
              
                
                
    @wca_live_check.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
