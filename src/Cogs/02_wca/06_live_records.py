import asyncio
import discord
from discord.ext import commands
import requests
import unicodedata

from discord.ext import tasks
from urllib.parse import quote

import src.wca_function as wca_function
import src.db as db
import src.functions as functions

# Static WCA Europe ISO2 list (sourced from /api/v0/countries on 2026-03-17).
EUROPEAN_ISO2 = {
    "AD","AL","AM","AT","AZ","BA","BE","BG","BY","CH","CY","CZ","DE","DK","EE","ES","FI","FR","GB","GE","GR","HR","HU","IE","IL","IS","IT","LI","LT","LU","LV","MC","MD","ME","MK","MT","NL","NO","PL","PT","RO","RS","RU","SE","SI","SK","SM","TR","UA","VA","XE","XK",
}
MEAN_EVENT_IDS = {"444bf", "555bf", "333fm", "666", "777"}
RECORDS_PAGE_URL = "https://www.worldcubeassociation.org/results/records"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

WCA_EVENT_NAMES = {
    "222": "2x2x2 Cube",
    "333": "3x3x3 Cube",
    "444": "4x4x4 Cube",
    "555": "5x5x5 Cube",
    "666": "6x6x6 Cube",
    "777": "7x7x7 Cube",
    "333bf": "3x3x3 Blindfolded",
    "333fm": "3x3x3 Fewest Moves",
    "333mbf": "3x3x3 Multi-Blind",
    "333oh": "3x3x3 One-Handed",
    "clock": "Clock",
    "minx": "Megaminx",
    "pyram": "Pyraminx",
    "skewb": "Skewb",
    "sq1": "Square-1",
    "444bf": "4x4x4 Blindfolded",
    "555bf": "5x5x5 Blindfolded",
}

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
    if tag in {"CR", "ER"} and bool(target.get("include_er")) and country_iso2 in EUROPEAN_ISO2:
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

def format_record_result(event_id, record_type, value):
    if event_id == "333fm" and record_type == "average":
        return f"{value / 100:.2f}"
    return functions.convert_to_human_frm(value, event_id)

def event_display_name(event_id):
    return WCA_EVENT_NAMES.get(event_id, event_id)

def canonical_text(value):
    if value is None:
        return "unknown"
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(
        char.lower()
        for char in text
        if char.isascii() and char.isalnum()
    ) or "unknown"

def load_live_record_targets():
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

def load_live_record_dedupe_row():
    return db.load_second_table_idd(4)

def _normalize_dedupe(dedupe):
    if isinstance(dedupe, list):
        return {"si": dedupe}
    if isinstance(dedupe, dict):
        return dedupe
    return {}

def _merge_dedupe_into(target_dedupe, source_dedupe):
    for target_key, source_records in source_dedupe.items():
        if not isinstance(source_records, list):
            continue
        target_records = target_dedupe.setdefault(target_key, [])
        target_record_set = {str(item) for item in target_records}
        for record_id in source_records:
            record_id = str(record_id)
            if record_id not in target_record_set:
                target_records.append(record_id)
                target_record_set.add(record_id)

def save_live_record_dedupe_row(row):
    latest_row = load_live_record_dedupe_row()
    if not isinstance(latest_row.get("data"), dict):
        latest_row["data"] = {}

    latest_dedupe = _normalize_dedupe(latest_row["data"].get("records_dedupe"))
    local_data = row.get("data") if isinstance(row.get("data"), dict) else {}
    local_dedupe = _normalize_dedupe(local_data.get("records_dedupe"))

    _merge_dedupe_into(latest_dedupe, local_dedupe)
    _merge_dedupe_into(local_dedupe, latest_dedupe)

    latest_row["data"]["records_dedupe"] = latest_dedupe
    row.setdefault("data", {})["records_dedupe"] = local_dedupe
    db.save_second_table_idd(latest_row)

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

def record_canonical_key(record, tag=None):
    tag = tag or display_tag(record)
    round_obj = record["result"]["round"]
    competition_event = round_obj["competitionEvent"]
    event_id = competition_event["event"]["id"]
    competition_name = competition_event["competition"].get("name")
    person = record["result"]["person"]
    person_id = person.get("wcaId") or person.get("name") or "unknown"
    result = record["attemptResult"]
    competition_key = canonical_text(competition_name)
    return f"record:{tag}:{event_id}:{record['type']}:{person_id}:{result}:{competition_key}"

def record_dedupe_key(record):
    try:
        return record_canonical_key(record)
    except (AttributeError, KeyError, TypeError):
        return None

def equivalent_record_dedupe_keys(record):
    tag = display_tag(record)
    if tag == "NR":
        tags = ("NR", "ER", "WR")
    elif tag == "ER":
        tags = ("ER", "WR")
    else:
        tags = (tag,)

    try:
        return [record_canonical_key(record, tag=tag) for tag in tags]
    except (AttributeError, KeyError, TypeError):
        return []

def already_sent_record(dedupe_map, target_key, record):
    record_key = record_dedupe_key(record)
    if record_key is None:
        print("[ERROR] record has no canonical dedupe key:", record)
        return True

    print("checking record", target_key, record_key)
    already_sent = dedupe_map.get(target_key, [])
    sent_keys = {str(item) for item in already_sent}
    sent = any(str(key) in sent_keys for key in equivalent_record_dedupe_keys(record))
    print(sent)
    return sent

def mark_sent_record(dedupe_map, target_key, record):
    record_key = record_dedupe_key(record)
    if record_key is None:
        print("[ERROR] record has no canonical dedupe key:", record)
        return

    already_sent = dedupe_map.setdefault(target_key, [])
    if record_key not in already_sent:
        print("ins", target_key, record_key)
        already_sent.append(record_key)

def records_url(country_name):
    return f"{RECORDS_PAGE_URL}?region={quote(country_name)}&show=mixed"

def country_iso2_from_wca_id(country_id):
    if not isinstance(country_id, str):
        return ""

    for country in getattr(wca_function, "c_data", []):
        if not isinstance(country, dict):
            continue
        if country.get("id") == country_id or country.get("name") == country_id:
            iso2 = country.get("iso2")
            if isinstance(iso2, str):
                return iso2

    for iso2, name in getattr(wca_function, "COUNTRIES_DICT", {}).items():
        if name == country_id:
            return iso2

    if country_id.upper() == "USA":
        return "US"
    return ""

def country_name_from_iso2(country_iso2):
    if not isinstance(country_iso2, str):
        return ""

    country_iso2 = country_iso2.upper()
    for country in getattr(wca_function, "c_data", []):
        if not isinstance(country, dict):
            continue
        if str(country.get("iso2", "")).upper() == country_iso2:
            name = country.get("name")
            if isinstance(name, str):
                return name

    for iso2, name in getattr(wca_function, "COUNTRIES_DICT", {}).items():
        if str(iso2).upper() == country_iso2 and isinstance(name, str):
            return name

    return ""

def official_record_regions_for_target(target):
    regions = []
    seen = set()

    def add(region_name, tag):
        key = (region_name, tag)
        if region_name and key not in seen:
            regions.append(key)
            seen.add(key)

    if bool(target.get("include_wr")):
        add("World", "WR")
    if bool(target.get("include_er")):
        add("_Europe", "ER")

    for country_iso2 in target.get("countries", []):
        country_name = country_name_from_iso2(country_iso2)
        if country_name:
            add(country_name, "NR")

    return regions

def official_record_row_to_record(row, tag):
    event_id = row.get("event_id")
    record_type = row.get("type")
    value = row.get("value")
    person_id = row.get("person_id")
    person_name = row.get("person_name")
    competition_id = row.get("competition_id")
    competition_name = row.get("competition_name")
    country_id = row.get("country_id")

    if not event_id or record_type not in {"single", "average"} or value is None:
        return None
    if not person_id or not competition_id:
        return None

    country_iso2 = country_iso2_from_wca_id(country_id)
    attempts = [
        {"result": attempt}
        for attempt in row.get("attempts", [])
        if isinstance(attempt, int)
    ]

    record = {
        "type": record_type,
        "tag": tag,
        "attemptResult": value,
        "result": {
            "attempts": attempts,
            "person": {
                "name": person_name or person_id,
                "wcaId": person_id,
                "country": {
                    "iso2": country_iso2,
                    "name": country_id or "",
                },
            },
            "round": {
                "id": row.get("round_id"),
                "competitionEvent": {
                    "event": {
                        "id": event_id,
                        "name": event_display_name(event_id),
                    },
                    "competition": {
                        "id": competition_id,
                        "name": competition_name or competition_id,
                    },
                },
            },
        },
    }
    record["id"] = record_canonical_key(record)
    return record

def fetch_official_records(region_name, tag):
    response = requests.get(
        records_url(region_name),
        headers=REQUEST_HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("rows", []) if isinstance(payload, dict) else []
    records = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        record = official_record_row_to_record(row, tag)
        if record is not None:
            records.append(record)
    return records

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

    result_value = format_record_result(event_id, record["type"], record["attemptResult"])
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

class liveRecordsCog(commands.Cog, name="live records monitor"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.records_check_lock = asyncio.Lock()
        self.wca_live_check.start()
        self.wca_official_records_check.start()


    @tasks.loop(seconds=300)
    async def wca_live_check(self):
        async with self.records_check_lock:
            await self._wca_live_check()

    async def _wca_live_check(self):
        targets = load_live_record_targets()
        if not targets:
            print("[WARN] no records targets configured")
            return

        dedupe_row = load_live_record_dedupe_row()
        target_keys = [
            str(target.get("key", "")).strip()
            for target in targets
            if str(target.get("key", "")).strip()
        ]
        dedupe_map = ensure_dedupe_map(dedupe_row, target_keys)

        print(f"[INFO] wca live record check ({', '.join(target_keys)})")
        try:
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
                timeout=20,
            )
            resp.raise_for_status()
            resp = resp.json()["data"]["recentRecords"]
        except Exception as exc:
            print(f"[ERROR] wca live record check failed: {exc}")
            return
        
      
        print(len(resp))

        for record in resp:
            print(record["id"])
            q = None

            for target in targets:
                target_key = str(target.get("key", "")).strip()
                if not target_key:
                    continue
                if not target_should_post_record(record, target):
                    continue
                if already_sent_record(dedupe_map, target_key, record):
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
                    try:
                        ch = await self.bot.fetch_channel(channel)
                    except Exception as exc:
                        print(f"[ERROR] records_channel not found for {target_key}: {channel} ({exc})")
                        continue

                try:
                    await ch.send(embed=q)
                except Exception as exc:
                    print(f"[ERROR] records send failed for {target_key} in channel {channel}: {exc}")
                    continue

                mark_sent_record(dedupe_map, target_key, record)
                save_live_record_dedupe_row(dedupe_row)
                print(f"[INFO] records sent target {target_key} to channel {channel}")

    @tasks.loop(hours=1)
    async def wca_official_records_check(self):
        async with self.records_check_lock:
            await self._wca_official_records_check()

    async def _wca_official_records_check(self):
        targets = load_live_record_targets()
        if not targets:
            print("[WARN] no official records targets configured")
            return

        dedupe_row = load_live_record_dedupe_row()
        target_keys = [
            str(target.get("key", "")).strip()
            for target in targets
            if str(target.get("key", "")).strip()
        ]
        dedupe_map = ensure_dedupe_map(dedupe_row, target_keys)
        records_cache = {}

        for target in targets:
            target_key = str(target.get("key", "")).strip()
            if not target_key:
                continue

            for region_name, tag in official_record_regions_for_target(target):
                cache_key = (region_name, tag)
                if cache_key not in records_cache:
                    try:
                        records_cache[cache_key] = await asyncio.to_thread(
                            fetch_official_records,
                            region_name,
                            tag,
                        )
                    except Exception as exc:
                        print(f"[ERROR] official {tag} check failed for {region_name}: {exc}")
                        records_cache[cache_key] = []

                records = records_cache[cache_key]
                print(
                    f"[INFO] official WCA {tag} check ({target_key}, {region_name}): "
                    f"{len(records)} current rows"
                )

                for record in records:
                    q = None

                    if not target_should_post_record(record, target):
                        continue

                    if already_sent_record(dedupe_map, target_key, record):
                        continue

                    if q is None:
                        print(f"OFFICIAL {tag} FOUND !!!", record)
                        q = build_record_embed(record)

                    channel = target.get("channel")
                    try:
                        channel = int(channel)
                    except (TypeError, ValueError):
                        print(f"[ERROR] invalid official records target channel for {target_key}: {channel}")
                        continue

                    ch = self.bot.get_channel(channel)
                    if ch is None:
                        try:
                            ch = await self.bot.fetch_channel(channel)
                        except Exception as exc:
                            print(f"[ERROR] official records channel not found for {target_key}: {channel} ({exc})")
                            continue

                    try:
                        await ch.send(embed=q)
                    except Exception as exc:
                        print(f"[ERROR] official records send failed for {target_key} in channel {channel}: {exc}")
                        continue

                    mark_sent_record(dedupe_map, target_key, record)
                    save_live_record_dedupe_row(dedupe_row)
                    print(f"[INFO] official {tag} sent target {target_key} to channel {channel}")

    @wca_live_check.before_loop
    @wca_official_records_check.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(liveRecordsCog(bot))
