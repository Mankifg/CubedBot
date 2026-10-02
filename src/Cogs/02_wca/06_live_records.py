import asyncio
import json
import os
import random
import secrets
import discord
import aiohttp
from discord.ext import commands
import requests
import traceback
import time
import unicodedata

from datetime import datetime
from discord.ext import tasks
from urllib.parse import quote
from zoneinfo import ZoneInfo

import src.wca_function as wca_function
import src.db as db
import src.functions as functions
from src.cubing_china_records import (
    CUBING_CHINA_API_BASE,
    active_wca_competitions,
    live_result_to_records,
)
from src.guild_access import ensure_primary_guild, primary_guild_ids

# Static WCA Europe ISO2 list (sourced from /api/v0/countries on 2026-03-17).
EUROPEAN_ISO2 = {
    "AD","AL","AM","AT","AZ","BA","BE","BG","BY","CH","CY","CZ","DE","DK","EE","ES","FI","FR","GB","GE","GR","HR","HU","IE","IL","IS","IT","LI","LT","LU","LV","MC","MD","ME","MK","MT","NL","NO","PL","PT","RO","RS","RU","SE","SI","SK","SM","TR","UA","VA","XE","XK",
}
MEAN_EVENT_IDS = {"444bf", "555bf", "333fm", "666", "777"}
RECORDS_PAGE_URL = "https://www.worldcubeassociation.org/results/records"
CUBING_CHINA_ENABLED = os.getenv(
    "CUBING_CHINA_RECORDS_ENABLED",
    "1",
).strip().lower() not in {"0", "false", "no", "off"}
CUBING_CHINA_SNAPSHOT_SECONDS = 60
CUBING_CHINA_GRACE_DAYS = 2
CUBING_CHINA_TIMEZONE = ZoneInfo("Asia/Shanghai")
RECORD_SOURCE_DEFAULTS = {
    "wca_live": True,
    "cubing_china": True,
    "wca_official": True,
}
RECORD_SOURCE_LABELS = {
    "wca_live": "WCA Live",
    "cubing_china": "Cubing China",
    "wca_official": "WCA official fallback",
}
RECORD_SOURCE_CONTROL_USER_IDS = {697176514676129933}
RECORD_SOURCE_CONTROL_ROLE_IDS = set()

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
    "fto": "Face-Turning Octahedron",
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

def trimmed_attempt_indices(event_id, times):
    if event_id in MEAN_EVENT_IDS or event_id == "333mbf" or len(times) != 5:
        return set()

    invalid_indices = [
        index
        for index, time in enumerate(times)
        if time in {-1, -2}
    ]
    worst_index = invalid_indices[-1] if invalid_indices else None

    valid_times = [
        (index, time)
        for index, time in enumerate(times)
        if isinstance(time, int) and time > 0
    ]
    if valid_times:
        best_value = min(time for _index, time in valid_times)
        best_index = next(
            index
            for index, time in valid_times
            if time == best_value
        )
    else:
        best_index = None

    if worst_index is None and valid_times:
        worst_value = max(time for _index, time in valid_times)
        worst_index = next(
            index
            for index, time in reversed(valid_times)
            if time == worst_value
        )

    return {
        index
        for index in {best_index, worst_index}
        if index is not None
    }

def format_record_attempts(event_id, times):
    trimmed_indices = trimmed_attempt_indices(event_id, times)
    formatted_times = []
    for index, time in enumerate(times):
        formatted_time = functions.convert_to_human_frm(time, event_id)
        if index in trimmed_indices:
            formatted_time = f"({formatted_time})"
        formatted_times.append(formatted_time)
    return ", ".join(formatted_times)

def format_record_solves(event_id, record_type, times, result_value):
    if event_id == "333mbf":
        return ""

    formatted_times = format_record_attempts(event_id, times)
    if record_type == "average":
        return formatted_times
    if event_id == "333fm" and times and all(isinstance(time, int) and time > 0 for time in times):
        return f"{sum(times) / len(times):.2f} | {formatted_times}"
    return f"{functions.convert_to_human_frm(functions.avg_of(times[:], event_id), event_id)} | {formatted_times}"

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

def normalize_record_source_states(data):
    configured = data.get("record_sources") if isinstance(data, dict) else None
    if not isinstance(configured, dict):
        configured = {}
    return {
        source: configured.get(source, default)
        if isinstance(configured.get(source, default), bool)
        else default
        for source, default in RECORD_SOURCE_DEFAULTS.items()
    }

def load_record_source_states():
    row = db.load_second_table_idd(3)
    return normalize_record_source_states(row.get("data"))

def save_record_source_state(source, enabled):
    if source not in RECORD_SOURCE_DEFAULTS:
        raise ValueError(f"unknown record source: {source}")

    row = db.load_second_table_idd(3)
    data = row.get("data")
    if not isinstance(data, dict):
        raise ValueError("record configuration has invalid data")

    states = normalize_record_source_states(data)
    states[source] = bool(enabled)
    data["record_sources"] = states
    db.save_second_table_idd(row)
    return states

def can_control_record_sources(member):
    if getattr(member, "id", None) in RECORD_SOURCE_CONTROL_USER_IDS:
        return True
    member_role_ids = {
        getattr(role, "id", None)
        for role in getattr(member, "roles", [])
    }
    return bool(member_role_ids & RECORD_SOURCE_CONTROL_ROLE_IDS)

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

def _normalize_pending(pending):
    if not isinstance(pending, dict):
        return {}

    normalized = {}
    for target_key, source_records in pending.items():
        target_key = str(target_key)
        if isinstance(source_records, dict):
            normalized[target_key] = {
                str(record_id): dict(metadata) if isinstance(metadata, dict) else {}
                for record_id, metadata in source_records.items()
            }
        elif isinstance(source_records, list):
            normalized[target_key] = {
                str(record_id): {}
                for record_id in source_records
            }
    return normalized

def _merge_pending_into(target_pending, source_pending):
    for target_key, source_records in source_pending.items():
        if not isinstance(source_records, dict):
            continue
        target_records = target_pending.setdefault(target_key, {})
        if not isinstance(target_records, dict):
            target_records = {}
            target_pending[target_key] = target_records
        for record_id, metadata in source_records.items():
            record_id = str(record_id)
            if record_id not in target_records:
                target_records[record_id] = (
                    dict(metadata) if isinstance(metadata, dict) else {}
                )

def _remove_sent_from_pending(pending_map, dedupe_map):
    for target_key, pending_records in pending_map.items():
        if not isinstance(pending_records, dict):
            continue
        sent_keys = {
            str(record_id)
            for record_id in dedupe_map.get(target_key, [])
        }
        for record_id in list(pending_records):
            if str(record_id) in sent_keys:
                del pending_records[record_id]

def _remove_pending_keys(pending_map, pending_removals):
    if not isinstance(pending_removals, dict):
        return

    for target_key, record_ids in pending_removals.items():
        pending_records = pending_map.get(str(target_key))
        if not isinstance(pending_records, dict):
            continue
        for record_id in record_ids:
            pending_records.pop(str(record_id), None)

def save_live_record_dedupe_row(row, pending_removals=None):
    latest_row = load_live_record_dedupe_row()
    if not isinstance(latest_row.get("data"), dict):
        latest_row["data"] = {}

    latest_dedupe = _normalize_dedupe(latest_row["data"].get("records_dedupe"))
    latest_pending = _normalize_pending(latest_row["data"].get("records_pending"))
    local_data = row.get("data") if isinstance(row.get("data"), dict) else {}
    local_dedupe = _normalize_dedupe(local_data.get("records_dedupe"))
    local_pending = _normalize_pending(local_data.get("records_pending"))

    _merge_dedupe_into(latest_dedupe, local_dedupe)
    _merge_dedupe_into(local_dedupe, latest_dedupe)
    _merge_pending_into(latest_pending, local_pending)
    _merge_pending_into(local_pending, latest_pending)
    _remove_pending_keys(latest_pending, pending_removals)
    _remove_pending_keys(local_pending, pending_removals)
    _remove_sent_from_pending(latest_pending, latest_dedupe)
    _remove_sent_from_pending(local_pending, local_dedupe)

    latest_row["data"]["records_dedupe"] = latest_dedupe
    latest_row["data"]["records_pending"] = latest_pending
    row.setdefault("data", {})["records_dedupe"] = local_dedupe
    row.setdefault("data", {})["records_pending"] = local_pending
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

def ensure_pending_map(row, target_keys):
    if not isinstance(row.get("data"), dict):
        row["data"] = {}

    pending = _normalize_pending(row["data"].get("records_pending"))
    row["data"]["records_pending"] = pending

    for key in target_keys:
        existing = pending.get(key)
        if not isinstance(existing, dict):
            pending[key] = {}

    return pending

def competition_dedupe_key(competition):
    if not isinstance(competition, dict):
        return "unknown"

    wca_id = competition.get("wcaId")
    if isinstance(wca_id, str) and wca_id.strip():
        return canonical_text(wca_id)

    return canonical_text(competition.get("name"))

def record_canonical_key(record, tag=None, person_identity=None):
    tag = tag or display_tag(record)
    round_obj = record["result"]["round"]
    competition_event = round_obj["competitionEvent"]
    event_id = competition_event["event"]["id"]
    competition = competition_event["competition"]
    person = record["result"]["person"]
    person_id = person_identity or person.get("wcaId") or person.get("name") or "unknown"
    result = record["attemptResult"]
    competition_key = competition_dedupe_key(competition)
    return f"record:{tag}:{event_id}:{record['type']}:{person_id}:{result}:{competition_key}"

def record_canonical_keys(record, tag=None):
    keys = [record_canonical_key(record, tag=tag)]
    person_name = record.get("result", {}).get("person", {}).get("name")
    if person_name:
        name_key = record_canonical_key(
            record,
            tag=tag,
            person_identity=f"name-{canonical_text(person_name)}",
        )
        if name_key not in keys:
            keys.append(name_key)
    return keys

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
        return [
            key
            for tag in tags
            for key in record_canonical_keys(record, tag=tag)
        ]
    except (AttributeError, KeyError, TypeError):
        return []

def record_group_key(record):
    try:
        round_obj = record["result"]["round"]
        competition_event = round_obj["competitionEvent"]
        event_id = competition_event["event"]["id"]
        competition = competition_event["competition"]
        person = record["result"]["person"]
        person_id = person.get("wcaId") or canonical_text(person.get("name"))
        attempts = tuple(
            attempt.get("result")
            for attempt in record["result"].get("attempts", [])
            if isinstance(attempt, dict)
        )
        return (
            display_tag(record),
            event_id,
            person_id,
            competition_dedupe_key(competition),
            str(round_obj.get("id")),
            attempts,
        )
    except (AttributeError, KeyError, TypeError):
        return None

def ordered_record_group(records):
    return sorted(
        records,
        key=lambda record: 0 if record.get("type") == "average" else 1,
    )

def grouped_record_batches(records):
    grouped = {}
    order = []

    for record in records:
        key = record_group_key(record)
        if key is None:
            order.append([record])
            continue
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(record)

    batches = []
    for item in order:
        if isinstance(item, list):
            batches.append(item)
            continue

        records_with_key = grouped[item]
        singles = [
            record
            for record in records_with_key
            if record.get("type") == "single"
        ]
        averages = [
            record
            for record in records_with_key
            if record.get("type") == "average"
        ]
        if len(records_with_key) == 2 and len(singles) == 1 and len(averages) == 1:
            batches.append(ordered_record_group(records_with_key))
        else:
            batches.extend([record] for record in records_with_key)

    return batches

def already_sent_record(dedupe_map, pending_map, target_key, record):
    record_key = record_dedupe_key(record)
    if record_key is None:
        print("[ERROR] record has no canonical dedupe key:", record)
        return True

    already_sent = dedupe_map.get(target_key, [])
    pending_records = pending_map.get(target_key, {})
    sent_keys = {str(item) for item in already_sent}
    pending_keys = {
        str(item)
        for item in pending_records.keys()
    } if isinstance(pending_records, dict) else set()
    sent = any(
        str(key) in sent_keys or str(key) in pending_keys
        for key in equivalent_record_dedupe_keys(record)
    )
    return sent

def mark_sent_record(dedupe_map, target_key, record):
    record_key = record_dedupe_key(record)
    if record_key is None:
        print("[ERROR] record has no canonical dedupe key:", record)
        return

    already_sent = dedupe_map.setdefault(target_key, [])
    for key in record_canonical_keys(record):
        if key not in already_sent:
            already_sent.append(key)

def mark_pending_record(pending_map, target_key, record, source):
    record_key = record_dedupe_key(record)
    if record_key is None:
        print("[ERROR] record has no canonical pending key:", record)
        return None

    pending_records = pending_map.setdefault(target_key, {})
    if not isinstance(pending_records, dict):
        pending_records = {}
        pending_map[target_key] = pending_records
    metadata = {
        "created_at": int(time.time()),
        "source": source,
    }
    for key in record_canonical_keys(record):
        if key not in pending_records:
            pending_records[key] = metadata
    return record_key

def clear_pending_record(pending_map, target_key, record):
    record_key = record_dedupe_key(record)
    if record_key is None:
        return []

    pending_records = pending_map.get(target_key)
    removed_keys = []
    if isinstance(pending_records, dict):
        for key in record_canonical_keys(record):
            if key in pending_records:
                del pending_records[key]
                removed_keys.append(key)
    return removed_keys

def reserve_pending_record(dedupe_row, pending_map, target_key, record, source):
    record_key = mark_pending_record(pending_map, target_key, record, source)
    if record_key is None:
        return False
    save_live_record_dedupe_row(dedupe_row)
    return True

def reserve_pending_records(dedupe_row, pending_map, target_key, records, source):
    for record in records:
        if record_dedupe_key(record) is None:
            print("[ERROR] record has no canonical pending key:", record)
            return False

    for record in records:
        record_key = mark_pending_record(pending_map, target_key, record, source)
        if record_key is None:
            return False
    save_live_record_dedupe_row(dedupe_row)
    return True

def mark_sent_and_clear_pending(dedupe_row, dedupe_map, pending_map, target_key, record):
    mark_sent_record(dedupe_map, target_key, record)
    record_keys = clear_pending_record(pending_map, target_key, record)
    pending_removals = {target_key: record_keys} if record_keys else None
    save_live_record_dedupe_row(dedupe_row, pending_removals=pending_removals)

def mark_sent_records_and_clear_pending(dedupe_row, dedupe_map, pending_map, target_key, records):
    pending_removal_keys = []
    for record in records:
        mark_sent_record(dedupe_map, target_key, record)
        pending_removal_keys.extend(
            clear_pending_record(pending_map, target_key, record)
        )
    pending_removals = (
        {target_key: pending_removal_keys}
        if pending_removal_keys
        else None
    )
    save_live_record_dedupe_row(dedupe_row, pending_removals=pending_removals)

def clear_pending_after_failed_send(dedupe_row, pending_map, target_key, record):
    record_keys = clear_pending_record(pending_map, target_key, record)
    pending_removals = {target_key: record_keys} if record_keys else None
    save_live_record_dedupe_row(dedupe_row, pending_removals=pending_removals)

def clear_pending_records_after_failed_send(dedupe_row, pending_map, target_key, records):
    pending_removal_keys = []
    for record in records:
        pending_removal_keys.extend(
            clear_pending_record(pending_map, target_key, record)
        )
    pending_removals = (
        {target_key: pending_removal_keys}
        if pending_removal_keys
        else None
    )
    save_live_record_dedupe_row(dedupe_row, pending_removals=pending_removals)

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
                        "wcaId": competition_id,
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

def record_result_label(record, event_id):
    shown_type = display_record_type(record["type"], event_id)
    if event_id == "333mbf":
        return "RESULT"
    if shown_type == "mean":
        return "MEAN"
    if record["type"] == "average":
        return "AVERAGE"
    return "SINGLE"

def record_group_title(show_tag, records, event_id):
    shown_types = [
        display_record_type(record["type"], event_id)
        for record in ordered_record_group(records)
    ]
    if len(shown_types) == 2:
        return f"{show_tag} {shown_types[0]} & {shown_types[1]}"
    return f"{show_tag} {shown_types[0]}"

def build_record_group_embed(records):
    records = ordered_record_group(records)
    record = records[0]
    show_tag = display_tag(record)
    person = record["result"]["person"]
    round_obj = record["result"]["round"]
    event_id = round_obj["competitionEvent"]["event"]["id"]
    titl = record_group_title(show_tag, records, event_id)

    if show_tag == "NR":
        q = discord.Embed(title=titl, color=discord.Colour.green())
    elif show_tag == "ER":
        q = discord.Embed(title=titl, color=discord.Colour.yellow())
    else:
        q = discord.Embed(title=titl, color=discord.Colour.red())

    person_wca_id = person.get("wcaId")
    person_value = (
        f'[{person_wca_id}]'
        f'(https://www.worldcubeassociation.org/persons/{person_wca_id})'
        if person_wca_id
        else "WCA ID pending"
    )
    q.add_field(
        name=f':flag_{person["country"]["iso2"].lower()}: {person["name"]}',
        value=person_value,
    )

    q.add_field(
        name=f'{round_obj["competitionEvent"]["event"]["name"]}',
        value=f'{round_obj["competitionEvent"]["competition"]["name"]}',
        inline=False,
    )

    average_record = next(
        (record for record in records if record.get("type") == "average"),
        None,
    )
    solves_record = average_record or record
    times = [
        el["result"]
        for el in solves_record["result"]["attempts"]
    ]
    solves_value = format_record_solves(
        event_id,
        solves_record["type"],
        times,
        format_record_result(
            event_id,
            solves_record["type"],
            solves_record["attemptResult"],
        ),
    )
    event_name = round_obj["competitionEvent"]["event"]["name"]
    comp_name = round_obj["competitionEvent"]["competition"]["name"]
    result_lines = f"{comp_name}\n\n"
    result_lines += "\n".join(
        f"**{record_result_label(record, event_id)}:** "
        f"`{format_record_result(event_id, record['type'], record['attemptResult'])}`"
        for record in records
    )
    if event_id != "333mbf":
        result_lines += f"\n\nSOLVES: {solves_value}"

    q.set_field_at(
        1,
        name=event_name,
        value=result_lines,
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

def build_record_embed(record):
    return build_record_group_embed([record])

class liveRecordsCog(commands.Cog, name="live records monitor"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.records_check_lock = asyncio.Lock()
        self.record_source_states = dict(RECORD_SOURCE_DEFAULTS)
        self.cubing_china_session = None
        self.cubing_china_competitions = {}
        self.cubing_china_workers = {}
        self.cubing_china_etags = {}
        self.cubing_china_round_revisions = {}
        self.cubing_china_viewer_id = secrets.token_hex(16)
        self.wca_live_check.start()
        self.wca_official_records_check.start()
        if CUBING_CHINA_ENABLED:
            self.cubing_china_discovery.start()

    def cog_unload(self):
        self.wca_live_check.cancel()
        self.wca_official_records_check.cancel()
        if CUBING_CHINA_ENABLED:
            self.cubing_china_discovery.cancel()
        self.bot.loop.create_task(self._shutdown_cubing_china())

    async def _shutdown_cubing_china(self):
        workers = list(self.cubing_china_workers.values())
        self.cubing_china_workers.clear()
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        if self.cubing_china_session is not None:
            await self.cubing_china_session.close()
            self.cubing_china_session = None

    async def _ensure_cubing_china_session(self):
        if self.cubing_china_session is None or self.cubing_china_session.closed:
            self.cubing_china_session = aiohttp.ClientSession(headers={
                "User-Agent": (
                    "CubedBot/1.2 record-monitor "
                    "(+https://github.com/Mankifg/CubedBot)"
                ),
                "Accept": "application/json",
            })
        return self.cubing_china_session

    def _refresh_record_source_states(self):
        self.record_source_states = load_record_source_states()
        return self.record_source_states

    def _record_source_enabled(self, source):
        enabled = bool(self.record_source_states.get(source, True))
        if source == "cubing_china" and not CUBING_CHINA_ENABLED:
            return False
        return enabled

    def _record_source_status_text(self):
        lines = []
        for source, label in RECORD_SOURCE_LABELS.items():
            configured = bool(self.record_source_states.get(source, True))
            effective = self._record_source_enabled(source)
            state = "enabled" if effective else "disabled"
            if source == "cubing_china" and configured and not effective:
                state += " (environment override)"
            lines.append(f"**{label}:** {state}")
        return "\n".join(lines)

    async def _run_enabled_record_source_once(self, source):
        try:
            if source == "cubing_china":
                if self._record_source_enabled(source):
                    await self._cubing_china_discovery(refresh_states=False)
                return

            async with self.records_check_lock:
                if not self._record_source_enabled(source):
                    return
                if source == "wca_live":
                    await self._wca_live_check()
                elif source == "wca_official":
                    await self._wca_official_records_check()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[ERROR] immediate {source} record check failed: {exc}")
            traceback.print_exc()

    @tasks.loop(hours=2)
    async def cubing_china_discovery(self):
        try:
            await self._cubing_china_discovery()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[ERROR] Cubing China competition discovery failed: {exc}")
            traceback.print_exc()

    async def _cubing_china_discovery(self, refresh_states=True):
        if refresh_states:
            self._refresh_record_source_states()
        if not self._record_source_enabled("cubing_china"):
            await self._sync_cubing_china_workers([])
            return
        if not load_live_record_targets():
            await self._sync_cubing_china_workers([])
            return

        session = await self._ensure_cubing_china_session()
        today = datetime.now(CUBING_CHINA_TIMEZONE).date()
        years = {today.year}
        if today.month == 1 and today.day <= 7:
            years.add(today.year - 1)
        competitions = []

        for year in sorted(years):
            skip = 0
            while True:
                async with session.get(
                    f"{CUBING_CHINA_API_BASE}/competitions",
                    params={"year": year, "take": 100, "skip": skip},
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)

                page = payload.get("data", []) if isinstance(payload, dict) else []
                if not isinstance(page, list):
                    raise ValueError("Cubing China competition list has invalid data")
                competitions.extend(page)

                total = payload.get("total", len(page))
                skip += len(page)
                if not page or skip >= total:
                    break

        active = active_wca_competitions(
            competitions,
            today,
            grace_days=CUBING_CHINA_GRACE_DAYS,
        )
        await self._sync_cubing_china_workers(active)

    async def _sync_cubing_china_workers(self, competitions):
        active_by_alias = {
            str(competition["alias"]): competition
            for competition in competitions
        }
        previous_aliases = set(self.cubing_china_competitions)
        active_aliases = set(active_by_alias)
        self.cubing_china_competitions = active_by_alias

        stopped_workers = []
        for alias in previous_aliases - active_aliases:
            worker = self.cubing_china_workers.pop(alias, None)
            if worker is not None:
                worker.cancel()
                stopped_workers.append(worker)
            self.cubing_china_etags.pop(alias, None)
            self.cubing_china_round_revisions.pop(alias, None)

        if stopped_workers:
            await asyncio.gather(*stopped_workers, return_exceptions=True)

        for alias in active_aliases:
            worker = self.cubing_china_workers.get(alias)
            if worker is None or worker.done():
                self.cubing_china_workers[alias] = self.bot.loop.create_task(
                    self._cubing_china_worker(alias)
                )

        if previous_aliases != active_aliases:
            print(
                "[INFO] Cubing China record monitor active competitions: "
                f"{len(active_aliases)}"
            )

    async def _cubing_china_worker(self, alias):
        snapshot_task = self.bot.loop.create_task(
            self._cubing_china_snapshot_loop(alias)
        )
        failures = 0
        try:
            while alias in self.cubing_china_competitions:
                connected_at = time.monotonic()
                try:
                    await self._fetch_cubing_china_snapshot(alias)
                    await self._consume_cubing_china_stream(alias)
                    raise aiohttp.ClientConnectionError("event stream closed")
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    if time.monotonic() - connected_at >= 60:
                        failures = 0
                    failures += 1
                    if failures == 1 or failures % 5 == 0:
                        print(
                            f"[WARN] Cubing China live stream reconnect {alias} "
                            f"after failure {failures}: {exc}"
                        )
                    delay = min(60, 2 ** min(failures, 5))
                    await asyncio.sleep(delay + random.random())
        finally:
            snapshot_task.cancel()
            await asyncio.gather(snapshot_task, return_exceptions=True)

    async def _cubing_china_snapshot_loop(self, alias):
        while alias in self.cubing_china_competitions:
            await asyncio.sleep(CUBING_CHINA_SNAPSHOT_SECONDS)
            try:
                await self._fetch_cubing_china_snapshot(alias)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[WARN] Cubing China record snapshot failed for {alias}: {exc}")

    async def _fetch_cubing_china_snapshot(self, alias):
        session = await self._ensure_cubing_china_session()
        headers = {}
        etag = self.cubing_china_etags.get(alias)
        if etag:
            headers["If-None-Match"] = etag

        async with session.get(
            f"{CUBING_CHINA_API_BASE}/competitions/{quote(alias, safe='')}/live/records",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 304:
                return
            response.raise_for_status()
            payload = await response.json(content_type=None)
            response_etag = response.headers.get("ETag")
            if response_etag:
                self.cubing_china_etags[alias] = response_etag

        results = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(results, list):
            raise ValueError("Cubing China records response has invalid data")
        await self._process_cubing_china_results(alias, results)

    async def _consume_cubing_china_stream(self, alias):
        session = await self._ensure_cubing_china_session()
        url = (
            f"{CUBING_CHINA_API_BASE}/competitions/"
            f"{quote(alias, safe='')}/live/stream"
        )
        timeout = aiohttp.ClientTimeout(total=None, sock_read=90)
        async with session.get(
            url,
            params={"viewerId": self.cubing_china_viewer_id},
            headers={"Accept": "text/event-stream"},
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            data_lines = []
            async for raw_line in response.content:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if line == "":
                    if data_lines:
                        await self._handle_cubing_china_event(
                            alias,
                            "\n".join(data_lines),
                        )
                    data_lines = []
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())

    async def _handle_cubing_china_event(self, alias, raw_data):
        try:
            event = json.loads(raw_data)
        except (TypeError, json.JSONDecodeError):
            return
        if not isinstance(event, dict) or event.get("type") == "heartbeat":
            return

        payload = event.get("payload")
        if not isinstance(payload, dict):
            return
        results = payload.get("upsertedResults")
        if not isinstance(results, list):
            return

        round_data = payload.get("round")
        revision_gap = False
        if isinstance(round_data, dict):
            round_id = round_data.get("id")
            revision = round_data.get("revision")
            if round_id is not None and isinstance(revision, int):
                revisions = self.cubing_china_round_revisions.setdefault(alias, {})
                previous = revisions.get(round_id)
                revision_gap = previous is not None and revision > previous + 1
                revisions[round_id] = max(revision, previous or revision)

        await self._process_cubing_china_results(alias, results)
        if revision_gap:
            await self._fetch_cubing_china_snapshot(alias)

    async def _process_cubing_china_results(self, alias, results):
        if not self._record_source_enabled("cubing_china"):
            return
        competition = self.cubing_china_competitions.get(alias)
        if not isinstance(competition, dict):
            return

        records = []
        for result in results:
            if not isinstance(result, dict):
                continue
            event_id = str(result.get("eventId") or "")
            event_name = WCA_EVENT_NAMES.get(event_id)
            if event_name is None:
                continue
            records.extend(
                live_result_to_records(result, competition, event_name)
            )
        if not records:
            return

        async with self.records_check_lock:
            targets = load_live_record_targets()
            if not targets:
                return
            dedupe_row = load_live_record_dedupe_row()
            target_keys = [
                str(target.get("key", "")).strip()
                for target in targets
                if str(target.get("key", "")).strip()
            ]
            dedupe_map = ensure_dedupe_map(dedupe_row, target_keys)
            pending_map = ensure_pending_map(dedupe_row, target_keys)
            for record_group in grouped_record_batches(records):
                await self._process_wca_live_records(
                    record_group,
                    targets,
                    dedupe_map,
                    pending_map,
                    dedupe_row,
                    source="cubing_china",
                )


    @tasks.loop(seconds=600)
    async def wca_live_check(self):
        try:
            async with self.records_check_lock:
                self._refresh_record_source_states()
                if not self._record_source_enabled("wca_live"):
                    return
                await self._wca_live_check()
        except Exception as exc:
            print(f"[ERROR] unexpected wca live record loop failure: {exc}")
            traceback.print_exc()

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
        pending_map = ensure_pending_map(dedupe_row, target_keys)

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
                                wcaId
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
        
        for records in grouped_record_batches(resp):
            try:
                await self._process_wca_live_records(
                    records,
                    targets,
                    dedupe_map,
                    pending_map,
                    dedupe_row,
                )
            except Exception as exc:
                record_ids = [
                    record.get("id")
                    for record in records
                    if isinstance(record, dict)
                ]
                print(f"[ERROR] failed to process WCA Live records {record_ids}: {exc}")
                traceback.print_exc()

    async def _process_wca_live_records(
        self,
        records,
        targets,
        dedupe_map,
        pending_map,
        dedupe_row,
        source="wca_live",
    ):
        for target in targets:
            target_key = str(target.get("key", "")).strip()
            if not target_key:
                continue

            send_records = []
            for record in records:
                if not target_should_post_record(record, target):
                    continue
                if already_sent_record(dedupe_map, pending_map, target_key, record):
                    continue
                send_records.append(record)

            if not send_records:
                continue

            send_records = ordered_record_group(send_records)
            q = build_record_group_embed(send_records)

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
                reserve_pending_records(
                    dedupe_row,
                    pending_map,
                    target_key,
                    send_records,
                    source,
                )
            except Exception as exc:
                print(f"[ERROR] records pending save failed for {target_key}: {exc}")
                traceback.print_exc()
                continue

            try:
                await ch.send(embed=q)
            except Exception as exc:
                print(f"[ERROR] records send failed for {target_key} in channel {channel}: {exc}")
                try:
                    clear_pending_records_after_failed_send(
                        dedupe_row,
                        pending_map,
                        target_key,
                        send_records,
                    )
                except Exception as cleanup_exc:
                    print(f"[ERROR] records pending cleanup failed for {target_key}: {cleanup_exc}")
                    traceback.print_exc()
                continue

            try:
                mark_sent_records_and_clear_pending(
                    dedupe_row,
                    dedupe_map,
                    pending_map,
                    target_key,
                    send_records,
                )
                print(
                    f"[INFO] {source} records sent target {target_key} "
                    f"to channel {channel}"
                )
            except Exception as exc:
                print(
                    f"[ERROR] records final dedupe save failed for {target_key}: {exc}. "
                    "Pending reservation remains."
                )
                traceback.print_exc()

    @tasks.loop(hours=1)
    async def wca_official_records_check(self):
        try:
            async with self.records_check_lock:
                self._refresh_record_source_states()
                if not self._record_source_enabled("wca_official"):
                    return
                await self._wca_official_records_check()
        except Exception as exc:
            print(f"[ERROR] unexpected official WCA record loop failure: {exc}")
            traceback.print_exc()

    @discord.command(
        name="recordsource",
        description="Enable or disable a global automatic record source.",
        guild_ids=primary_guild_ids(),
    )
    @discord.option(
        name="source",
        description="Record source to control.",
        choices=list(RECORD_SOURCE_DEFAULTS),
        required=True,
    )
    @discord.option(
        name="enabled",
        description="Whether this source should be enabled.",
        input_type=bool,
        required=True,
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def recordsource(self, ctx, source: str, enabled: bool):
        if not await ensure_primary_guild(ctx, self.bot):
            return
        if not can_control_record_sources(ctx.author):
            await ctx.respond(
                "You don't have permission to control record sources.",
                ephemeral=True,
            )
            return
        await ctx.defer(ephemeral=True)

        apply_error = None
        try:
            async with self.records_check_lock:
                self.record_source_states = save_record_source_state(source, enabled)
                if source == "cubing_china" and not self._record_source_enabled(source):
                    try:
                        await self._sync_cubing_china_workers([])
                    except Exception as exc:
                        apply_error = exc
                        print(f"[ERROR] Cubing China worker shutdown failed: {exc}")
                        traceback.print_exc()
        except Exception as exc:
            print(f"[ERROR] record source setting update failed: {exc}")
            traceback.print_exc()
            await ctx.edit(
                content="The source setting could not be saved. Nothing was changed.",
            )
            return

        effective = self._record_source_enabled(source)
        if enabled and effective:
            self.bot.loop.create_task(self._run_enabled_record_source_once(source))

        print(
            f"[INFO] record source {source} set to {enabled} "
            f"by user {ctx.author.id}"
        )

        response = self._record_source_status_text()
        if apply_error is not None:
            response += (
                "\n\nThe setting was saved, but the existing Cubing China "
                "workers could not be stopped cleanly."
            )
        await ctx.edit(content=response)

    @discord.command(
        name="recordsources",
        description="Show global automatic record source states.",
        guild_ids=primary_guild_ids(),
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def recordsources(self, ctx):
        if not await ensure_primary_guild(ctx, self.bot):
            return
        if not can_control_record_sources(ctx.author):
            await ctx.respond(
                "You don't have permission to view record source controls.",
                ephemeral=True,
            )
            return
        await ctx.defer(ephemeral=True)

        try:
            self._refresh_record_source_states()
        except Exception as exc:
            print(f"[ERROR] record source settings load failed: {exc}")
            traceback.print_exc()
            await ctx.edit(
                content="The source settings could not be loaded.",
            )
            return

        await ctx.edit(content=self._record_source_status_text())

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
        pending_map = ensure_pending_map(dedupe_row, target_keys)
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

                for record_group in grouped_record_batches(records):
                    try:
                        await self._process_official_records(
                            record_group,
                            target,
                            target_key,
                            tag,
                            dedupe_map,
                            pending_map,
                            dedupe_row,
                        )
                    except Exception as exc:
                        record_ids = [
                            record.get("id")
                            for record in record_group
                            if isinstance(record, dict)
                        ]
                        print(f"[ERROR] failed to process official {tag} records {record_ids}: {exc}")
                        traceback.print_exc()

    async def _process_official_records(
        self,
        records,
        target,
        target_key,
        tag,
        dedupe_map,
        pending_map,
        dedupe_row,
    ):
        send_records = []
        for record in records:
            if not target_should_post_record(record, target):
                continue
            if already_sent_record(dedupe_map, pending_map, target_key, record):
                continue
            send_records.append(record)

        if not send_records:
            return

        send_records = ordered_record_group(send_records)
        q = build_record_group_embed(send_records)

        channel = target.get("channel")
        try:
            channel = int(channel)
        except (TypeError, ValueError):
            print(f"[ERROR] invalid official records target channel for {target_key}: {channel}")
            return

        ch = self.bot.get_channel(channel)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(channel)
            except Exception as exc:
                print(f"[ERROR] official records channel not found for {target_key}: {channel} ({exc})")
                return

        try:
            reserve_pending_records(
                dedupe_row,
                pending_map,
                target_key,
                send_records,
                f"official_{tag.lower()}",
            )
        except Exception as exc:
            print(f"[ERROR] official records pending save failed for {target_key}: {exc}")
            traceback.print_exc()
            return

        try:
            await ch.send(embed=q)
        except Exception as exc:
            print(f"[ERROR] official records send failed for {target_key} in channel {channel}: {exc}")
            try:
                clear_pending_records_after_failed_send(
                    dedupe_row,
                    pending_map,
                    target_key,
                    send_records,
                )
            except Exception as cleanup_exc:
                print(f"[ERROR] official records pending cleanup failed for {target_key}: {cleanup_exc}")
                traceback.print_exc()
            return

        try:
            mark_sent_records_and_clear_pending(
                dedupe_row,
                dedupe_map,
                pending_map,
                target_key,
                send_records,
            )
            print(f"[INFO] official {tag} sent target {target_key} to channel {channel}")
        except Exception as exc:
            print(
                f"[ERROR] official {tag} final dedupe save failed for {target_key}: {exc}. "
                "Pending reservation remains."
            )
            traceback.print_exc()

    @wca_live_check.before_loop
    @wca_official_records_check.before_loop
    @cubing_china_discovery.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(liveRecordsCog(bot))
