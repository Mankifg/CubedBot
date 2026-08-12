import discord
from discord.ext import commands

from discord.ext import tasks
import asyncio
import calendar
from datetime import datetime as dt, timedelta, timezone

import src.wca_function as wca_function
import src.db as db
import src.hardstorage as hardstorage

LAT,LON = 46.0569, 14.5058
REMINDER_REACTION = "🔔"
REMINDER_MINUTES_BEFORE = 60
REGISTRATION_REMINDER_CHECK_SECONDS = 60
ANNOUNCER_LOOKAHEAD_MONTHS = 12
WCA_COMPETITION_URL = "https://www.worldcubeassociation.org/competitions/{}"


def _people_field(singular, dual, plural, people):
    if not isinstance(people, list):
        people = []
    names = [
        person.get("name")
        for person in people
        if isinstance(person, dict) and person.get("name")
    ]
    if len(names) == 1:
        label = singular
    elif len(names) == 2:
        label = dual
    else:
        label = plural
    if not names:
        return label, "-"
    if len(names) <= 5:
        return label, "\n".join(names)
    return label, ", ".join(names)


def _format_event_ids(event_ids):
    events = []
    unknown_event_ids = []
    for event_id in event_ids:
        event_label = hardstorage.SHORT_DICTIONARY.get(event_id)
        if event_label is None:
            event_label = str(event_id)
            unknown_event_ids.append(event_label)
        events.append(event_label)
    return events, unknown_event_ids


def _parse_wca_datetime(value):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    try:
        parsed = dt.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_wca_datetime(value):
    parsed = _parse_wca_datetime(value) if isinstance(value, str) else value
    if parsed is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_announcer_data(row):
    if not isinstance(row.get("data"), dict):
        row["data"] = {}
    return row["data"]


def _ensure_announcer_dedupe(row):
    data = _ensure_announcer_data(row)
    already_printed_comps = data.get("announcer_dedupe")
    if not isinstance(already_printed_comps, list):
        already_printed_comps = []
        data["announcer_dedupe"] = already_printed_comps
    return already_printed_comps


def _ensure_registration_reminders(row):
    data = _ensure_announcer_data(row)
    reminders = data.get("registration_reminders")
    if not isinstance(reminders, dict):
        reminders = {}
        data["registration_reminders"] = reminders
    return reminders


def _registration_reminder_from_comp(data, announcement_channel_id, announcement_message_id):
    registration_open = _parse_wca_datetime(data.get("registration_open"))
    if registration_open is None:
        return None

    now = dt.now(timezone.utc)
    if registration_open <= now:
        return None

    remind_at = registration_open - timedelta(minutes=REMINDER_MINUTES_BEFORE)
    country = str(data.get("country", "")).upper()
    reminder_target = "si" if country == "SI" else "abroad"
    comp_id = data.get("id")

    return {
        "competition_id": comp_id,
        "competition_name": data.get("name", comp_id),
        "competition_url": data.get("url") or WCA_COMPETITION_URL.format(comp_id),
        "country": country,
        "target": reminder_target,
        "announcement_channel": str(announcement_channel_id),
        "announcement_message": str(announcement_message_id),
        "registration_open": _format_wca_datetime(registration_open),
        "remind_at": _format_wca_datetime(remind_at),
        "sent": False,
    }


def _registration_reminder_channels():
    row = db.load_second_table_idd(5)
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    channels = data.get("registration_reminder_channels")
    if not isinstance(channels, dict):
        return {}
    return {
        "si": channels.get("si"),
        "abroad": channels.get("abroad"),
    }


class annouceCog(commands.Cog, name="annouce command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.announcer_lock = asyncio.Lock()
        self.check.start()
        self.registration_reminder_check.start()

    @tasks.loop(seconds=3600)
    async def check(self):
        try:
            async with self.announcer_lock:
                await self._check()
        except Exception as exc:
            print(f"[ERROR] announcer check failed: {exc}")

    async def _check(self):

        all_comps = []
        c_month = dt.now().month
        c_year = dt.now().year

        range_start = dt(c_year, c_month, 1).date()
        end_month = c_month + ANNOUNCER_LOOKAHEAD_MONTHS - 1
        end_year = c_year
        while end_month > 12:
            end_month -= 12
            end_year += 1
        range_end = dt(
            end_year,
            end_month,
            calendar.monthrange(end_year, end_month)[1],
        ).date()

        try:
            data = await asyncio.to_thread(wca_function.find_by_date_range, range_start, range_end)
        except Exception as exc:
            print(f"[ERROR] announcer fetch failed for {range_start} - {range_end}: {exc}")
            data = []

        if data is not None:
            all_comps.extend(data)

        distanced_comps = wca_function.filter_by_distance(all_comps)
        special_comps = [
            comp for comp in all_comps
            if wca_function.is_special_fmc_comp(comp.get("name"))
        ]
        distanced_comp_ids = {comp["id"] for comp in distanced_comps}
        merged_comps = list(distanced_comps)
        for comp in special_comps:
            if comp["id"] not in distanced_comp_ids:
                merged_comps.append(comp)
                distanced_comp_ids.add(comp["id"])
        print(
            "[INFO] announcer scan: "
            f"{len(all_comps)} WCA comps, "
            f"{len(distanced_comps)} nearby, "
            f"{len(special_comps)} special, "
            f"{len(merged_comps)} candidates"
        )

        dedupe_row = db.load_second_table_idd(6)
        already_printed_comps = _ensure_announcer_dedupe(dedupe_row)
        registration_reminders = _ensure_registration_reminders(dedupe_row)

        channel = db.load_second_table_idd(5)["data"]["announcer_channel"]
        channel = int(channel)
        ch = self.bot.get_channel(channel)
        if ch is None:
            print(f"[ERROR] announcer_channel not found: {channel}")
            return

        final_comps = []

        for comp in merged_comps:
            comp_id = comp["id"]

            if not comp_id in already_printed_comps:
                final_comps.append(comp)


        for comp in final_comps:

            comp_id = comp["id"]
            try:
                success, data = await asyncio.to_thread(wca_function.get_comp_data, comp_id)

                if not success:
                    continue
                is_special_fmc = wca_function.is_special_fmc_comp(data["name"])
                q = discord.Embed(
                    title=f"{wca_function.comp_title_prefix(data['name'], data['country'])} | {data['name']}",
                    description=f"{data['city']}, {wca_function.COUNTRIES_DICT.get(data['country'])} | [{data['id']}](https://www.worldcubeassociation.org/competitions/{data['id']})",
                    color=discord.Colour.blue(),
                )
                start_date = data["date"]["from"]
                end_date = data["date"]["till"]
                date = wca_function.format_comp_date(
                    data["name"],
                    start_date,
                    end_date,
                    data["date"]["numberOfDays"],
                )

                q.add_field(name="Datum", value=date, inline=False)

                #*********
                events, unknown_event_ids = _format_event_ids(data["events"])
                if unknown_event_ids:
                    print(f"[WARN] unknown event ids for {comp_id}: {unknown_event_ids}")

                q.add_field(name="Discipline", value=", ".join(events), inline=False)

                if not is_special_fmc:
                    organizer_label, organizer_value = _people_field(
                        "Organizator",
                        "Organizatorja",
                        "Organizatorji",
                        data["organisers"],
                    )
                    q.add_field(name=organizer_label, value=organizer_value, inline=True)

                    delegate_label, delegate_value = _people_field(
                        "WCA delegat",
                        "WCA delegata",
                        "WCA delegati",
                        data["wcaDelegates"],
                    )
                    q.add_field(name=delegate_label, value=delegate_value, inline=True)

                    q.add_field(name="Prizorišče", value=f"{data['venue']['name']}\n{data['venue']['address']}", inline=False,)

                if data["externalWebsite"]:
                    q.add_field(name="Spletna stran", value=data["externalWebsite"], inline=False)
            except Exception as exc:
                print(f"[ERROR] announcer embed build failed for {comp_id}: {exc}")
                continue

            try:
                send_msg = await ch.send(embed=q)
            except Exception as exc:
                print(f"[ERROR] announcer send failed for {comp_id}: {exc}")
                continue

            for reaction in ("🟢", "🟡", "🔴"):
                try:
                    await send_msg.add_reaction(reaction)
                except Exception as exc:
                    print(f"[WARN] announcer reaction {reaction} failed for {comp_id}: {exc}")
            reminder = _registration_reminder_from_comp(data, ch.id, send_msg.id)
            if reminder is not None:
                registration_reminders[comp_id] = reminder
                try:
                    await send_msg.add_reaction(REMINDER_REACTION)
                except Exception as exc:
                    print(f"[WARN] announcer reminder reaction failed for {comp_id}: {exc}")

            if comp_id not in already_printed_comps:
                already_printed_comps.append(comp_id)
            try:
                db.save_second_table_idd(dedupe_row)
            except Exception as exc:
                print(f"[ERROR] announcer dedupe save failed after {comp_id}: {exc}")

            await asyncio.sleep(5)

    @tasks.loop(seconds=REGISTRATION_REMINDER_CHECK_SECONDS)
    async def registration_reminder_check(self):
        try:
            async with self.announcer_lock:
                await self._registration_reminder_check()
        except Exception as exc:
            print(f"[ERROR] registration reminder check failed: {exc}")

    async def _registration_reminder_check(self):
        dedupe_row = db.load_second_table_idd(6)
        reminders = _ensure_registration_reminders(dedupe_row)
        if not reminders:
            return

        reminder_channels = _registration_reminder_channels()
        changed = False

        for comp_id, reminder in list(reminders.items()):
            if not isinstance(reminder, dict):
                continue
            if reminder.get("sent") or reminder.get("pending"):
                continue

            registration_open = _parse_wca_datetime(reminder.get("registration_open"))
            remind_at = _parse_wca_datetime(reminder.get("remind_at"))
            if registration_open is None or remind_at is None:
                changed = await self._refresh_registration_reminder(comp_id, reminder) or changed
                continue

            now = dt.now(timezone.utc)
            if now < remind_at:
                continue

            changed = await self._refresh_registration_reminder(comp_id, reminder) or changed
            registration_open = _parse_wca_datetime(reminder.get("registration_open"))
            remind_at = _parse_wca_datetime(reminder.get("remind_at"))
            now = dt.now(timezone.utc)

            if registration_open is None or remind_at is None:
                continue
            if now < remind_at:
                continue
            if now >= registration_open:
                reminder["sent"] = True
                reminder["sent_at"] = _format_wca_datetime(now)
                reminder["skipped"] = "registration_already_open"
                changed = True
                continue

            users = await self._reminder_reaction_users(reminder)
            if users is None:
                continue
            reminder["subscriber_count"] = len(users)
            reminder["subscriber_ids"] = [str(user.id) for user in users]
            reminder["subscriber_names"] = [str(user) for user in users]
            if not users:
                reminder["sent"] = True
                reminder["sent_at"] = _format_wca_datetime(now)
                reminder["skipped"] = "no_subscribers"
                changed = True
                continue

            channel_id = reminder_channels.get(reminder.get("target"))
            if not channel_id:
                print(f"[ERROR] registration reminder channel not configured for {reminder.get('target')}")
                continue

            channel = await self._fetch_channel(channel_id, "registration reminder")
            if channel is None:
                continue

            reminder["pending"] = True
            reminder["pending_at"] = _format_wca_datetime(now)
            try:
                db.save_second_table_idd(dedupe_row)
            except Exception as exc:
                print(f"[ERROR] registration reminder pending save failed for {comp_id}: {exc}")
                reminder.pop("pending", None)
                reminder.pop("pending_at", None)
                continue

            try:
                await self._send_registration_reminder(channel, reminder, users, registration_open)
            except Exception as exc:
                print(f"[ERROR] registration reminder send failed for {comp_id}: {exc}")
                reminder.pop("pending", None)
                reminder.pop("pending_at", None)
                try:
                    db.save_second_table_idd(dedupe_row)
                except Exception as cleanup_exc:
                    print(f"[ERROR] registration reminder pending cleanup failed for {comp_id}: {cleanup_exc}")
                continue

            reminder["sent"] = True
            reminder["sent_at"] = _format_wca_datetime(dt.now(timezone.utc))
            reminder.pop("pending", None)
            reminder.pop("pending_at", None)
            try:
                db.save_second_table_idd(dedupe_row)
            except Exception as exc:
                print(f"[ERROR] registration reminder final save failed for {comp_id}: {exc}. Pending remains.")
                reminder["sent"] = False
                reminder.pop("sent_at", None)
                reminder["pending"] = True
                reminder["pending_at"] = _format_wca_datetime(now)

        if changed:
            db.save_second_table_idd(dedupe_row)

    async def _refresh_registration_reminder(self, comp_id, reminder):
        success, data = await asyncio.to_thread(wca_function.get_comp_data, comp_id)
        if not success:
            print(f"[WARN] could not refresh registration reminder for {comp_id}")
            return False

        registration_open = _parse_wca_datetime(data.get("registration_open"))
        if registration_open is None:
            print(f"[WARN] registration_open missing for {comp_id}")
            return False

        old_registration_open = _parse_wca_datetime(reminder.get("registration_open"))
        if old_registration_open == registration_open:
            return False

        remind_at = registration_open - timedelta(minutes=REMINDER_MINUTES_BEFORE)
        country = str(data.get("country", "")).upper()
        reminder["competition_name"] = data.get("name", comp_id)
        reminder["competition_url"] = data.get("url") or WCA_COMPETITION_URL.format(comp_id)
        reminder["country"] = country
        reminder["target"] = "si" if country == "SI" else "abroad"
        reminder["registration_open"] = _format_wca_datetime(registration_open)
        reminder["remind_at"] = _format_wca_datetime(remind_at)
        return True

    async def _reminder_reaction_users(self, reminder):
        channel = await self._fetch_channel(reminder.get("announcement_channel"), "announcement")
        if channel is None:
            return None

        best_users = []
        for attempt in range(2):
            try:
                message = await channel.fetch_message(int(reminder.get("announcement_message")))
            except discord.NotFound:
                return []
            except Exception as exc:
                print(f"[ERROR] could not fetch announcement message for reminder: {exc}")
                return None

            for reaction in message.reactions:
                if str(reaction.emoji) != REMINDER_REACTION:
                    continue

                all_users = await self._reaction_users(reaction)
                users = [
                    user
                    for user in all_users
                    if not getattr(user, "bot", False)
                ]
                best_users = users

                if len(all_users) >= reaction.count:
                    return users

                print(
                    "[WARN] reminder reaction user count mismatch for "
                    f"{reminder.get('competition_id')}: "
                    f"reaction.count={reaction.count}, api_users={len(all_users)} "
                    f"(attempt {attempt + 1}/2)"
                )
                await asyncio.sleep(3)
                break
            else:
                return []

        return best_users

    async def _reaction_users(self, reaction):
        users_by_id = {}

        async def collect(**kwargs):
            async for user in reaction.users(**kwargs):
                users_by_id[user.id] = user

        try:
            await collect()
        except Exception as exc:
            print(f"[ERROR] could not fetch reaction users: {exc}")
            raise

        reaction_type = getattr(discord, "ReactionType", None)
        burst_type = getattr(reaction_type, "burst", None) if reaction_type is not None else None
        if burst_type is not None:
            try:
                await collect(type=burst_type)
            except Exception as exc:
                print(f"[WARN] could not fetch burst reaction users: {exc}")

        return list(users_by_id.values())

    async def _fetch_channel(self, channel_id, label):
        try:
            channel_id = int(channel_id)
        except (TypeError, ValueError):
            print(f"[ERROR] invalid {label} channel id: {channel_id}")
            return None

        channel = self.bot.get_channel(channel_id)
        if channel is not None:
            return channel

        try:
            return await self.bot.fetch_channel(channel_id)
        except Exception as exc:
            print(f"[ERROR] {label} channel not found: {channel_id} ({exc})")
            return None

    async def _send_registration_reminder(self, channel, reminder, users, registration_open):
        mentions = " ".join(user.mention for user in users)
        competition_name = reminder.get("competition_name") or reminder.get("competition_id")
        competition_url = reminder.get("competition_url") or WCA_COMPETITION_URL.format(reminder.get("competition_id"))
        open_timestamp = int(registration_open.timestamp())
        content = (
            f"🔔 Prijave za **[{competition_name}]({competition_url})** se odprejo "
            f"ob <t:{open_timestamp}:t> (<t:{open_timestamp}:R>).\n\n"
            f"{mentions}"
        )
        await channel.send(
            content,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False,
            ),
        )

    @check.before_loop
    @registration_reminder_check.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(annouceCog(bot))
