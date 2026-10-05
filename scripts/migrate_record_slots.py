#!/usr/bin/env python3
"""Build and safely apply the v2 slot-only record history to vars.id=4."""

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src import db  # noqa: E402
from src.cubing_china_records import (  # noqa: E402
    CUBING_CHINA_API_BASE,
    active_wca_competitions,
    live_result_to_records,
)
from src.record_slots import (  # noqa: E402
    EUROPEAN_ISO2,
    RECORD_STORAGE_VERSION,
    empty_record_slots,
    record_aliases,
    seed_record,
)


REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
OFFICIAL_RECORDS_URL = "https://www.worldcubeassociation.org/results/records"
WCA_COUNTRIES_URL = "https://www.worldcubeassociation.org/api/v0/countries"
WCA_LIVE_URL = "https://live.worldcubeassociation.org/api/graphql"
FALSE_LEGACY_KEYS = {
    "record:WR:333:single:2019WUJU07:232:guangzhougrandopen2026",
    "record:WR:333:single:name-junyuanwu:232:guangzhougrandopen2026",
    "record:WR:333:single:2019WUJU07:1752:guangzhougrandopen2026",
    "record:WR:333:single:name-junyuanwu:1752:guangzhougrandopen2026",
    "record:ER:clock:average:2019TARA09:513:guangzhougrandopen2026",
    "record:ER:clock:average:name-timofeitarasenko:513:guangzhougrandopen2026",
    "record:ER:clock:average:2019TARA09:587:guangzhougrandopen2026",
    "record:ER:clock:average:name-timofeitarasenko:587:guangzhougrandopen2026",
}
LEGACY_KEY_RE = re.compile(
    r"^record:(WR|ER|NR):([^:]+):(single|average):([^:]+):(-?\d+):([^:]+)$"
)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_hash(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_ref():
    hostname = urlparse(os.environ.get("SUPA_URL", "")).hostname or ""
    return hostname.split(".", 1)[0]


def normalized_tag(record):
    tag = str(record.get("tag") or "").upper()
    return "ER" if tag == "CR" else tag


def person_country(record):
    return str(
        record.get("result", {})
        .get("person", {})
        .get("country", {})
        .get("iso2", "")
    ).upper()


def relevant_record(record):
    tag = normalized_tag(record)
    country = person_country(record)
    return (
        tag == "WR"
        or (tag == "ER" and country in EUROPEAN_ISO2)
        or (tag == "NR" and country in {"SI", "HR"})
    )


def target_should_receive(record, target):
    tag = normalized_tag(record)
    country = person_country(record)
    countries = {
        str(value).upper()
        for value in target.get("countries", [])
        if isinstance(value, str)
    }
    if tag == "NR":
        return country in countries
    if tag == "ER":
        return bool(target.get("include_er")) and country in EUROPEAN_ISO2
    return tag == "WR" and bool(target.get("include_wr"))


def baseline_deliveries(record, targets, source):
    return {
        str(target["key"]): {
            "announced_as": normalized_tag(record),
            "source": source,
            "sent_at": None,
            "message_id": None,
        }
        for target in targets
        if target.get("key") and target_should_receive(record, target)
    }


def country_map():
    response = requests.get(
        WCA_COUNTRIES_URL,
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    countries = response.json()
    return {
        str(country.get("id") or country.get("name")): str(country.get("iso2") or "")
        for country in countries
        if isinstance(country, dict)
    }


def official_row_to_record(row, tag, countries):
    event_id = row.get("event_id")
    record_type = row.get("type")
    value = row.get("value")
    person_id = row.get("person_id")
    competition_id = row.get("competition_id")
    if (
        not event_id
        or record_type not in {"single", "average"}
        or not isinstance(value, int)
        or value <= 0
        or not person_id
        or not competition_id
    ):
        return None
    country_id = str(row.get("country_id") or "")
    return {
        "type": record_type,
        "tag": tag,
        "attemptResult": value,
        "result": {
            "attempts": [
                {"result": attempt}
                for attempt in row.get("attempts", [])
                if isinstance(attempt, int)
            ],
            "person": {
                "name": row.get("person_name") or person_id,
                "wcaId": person_id,
                "country": {
                    "iso2": countries.get(country_id, ""),
                    "name": country_id,
                },
            },
            "round": {
                "id": row.get("round_id"),
                "competitionEvent": {
                    "event": {"id": event_id, "name": event_id},
                    "competition": {
                        "id": competition_id,
                        "wcaId": competition_id,
                        "name": row.get("competition_name") or competition_id,
                    },
                },
            },
        },
    }


def fetch_official_records():
    countries = country_map()
    records = []
    for region, tag in (
        ("World", "WR"),
        ("_Europe", "ER"),
        ("Slovenia", "NR"),
        ("Croatia", "NR"),
    ):
        response = requests.get(
            OFFICIAL_RECORDS_URL,
            params={"region": region, "show": "mixed"},
            headers=REQUEST_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json().get("rows", [])
        for row in rows:
            if not isinstance(row, dict):
                continue
            record = official_row_to_record(row, tag, countries)
            if record is not None and relevant_record(record):
                records.append(record)
    return records


def fetch_wca_live_records():
    response = requests.post(
        WCA_LIVE_URL,
        json={"query": """
            query {
              recentRecords {
                id type tag attemptResult
                result {
                  attempts { result }
                  person { name wcaId country { iso2 name } }
                  round {
                    id
                    competitionEvent {
                      event { id name }
                      competition { id name wcaId }
                    }
                  }
                }
              }
            }
        """},
        timeout=30,
    )
    response.raise_for_status()
    records = response.json().get("data", {}).get("recentRecords", [])
    return [record for record in records if relevant_record(record)]


def fetch_cubing_china_records():
    today = date.today()
    competitions = []
    for year in {today.year - 1, today.year}:
        skip = 0
        while True:
            response = requests.get(
                f"{CUBING_CHINA_API_BASE}/competitions",
                params={"year": year, "take": 100, "skip": skip},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            page = payload.get("data", [])
            competitions.extend(page)
            skip += len(page)
            if not page or skip >= payload.get("total", len(page)):
                break

    records = []
    for competition in active_wca_competitions(competitions, today, grace_days=2):
        alias = competition["alias"]
        response = requests.get(
            f"{CUBING_CHINA_API_BASE}/competitions/{alias}/live/records",
            timeout=30,
        )
        response.raise_for_status()
        for result in response.json().get("data", []):
            if not isinstance(result, dict):
                continue
            event_id = str(result.get("eventId") or "")
            records.extend(live_result_to_records(result, competition, event_id))
    return [record for record in records if relevant_record(record)]


def live_fingerprint(record):
    result = record["result"]
    round_obj = result["round"]
    payload = {
        "aliases": record_aliases(record),
        "tag": normalized_tag(record),
        "round_id": round_obj.get("id"),
        "attempts": [
            attempt.get("result")
            for attempt in result.get("attempts", [])
            if isinstance(attempt, dict)
        ],
    }
    return canonical_hash(payload)


def fetch_live_inventory():
    return {
        "wca_live": fetch_wca_live_records(),
        "cubing_china": fetch_cubing_china_records(),
    }


def capture_baseline(path):
    inventory = fetch_live_inventory()
    payload = {
        "created_at": utc_now_iso(),
        "records": inventory,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "baseline": str(path),
        "created_at": payload["created_at"],
        "wca_live": len(inventory["wca_live"]),
        "cubing_china": len(inventory["cubing_china"]),
    }, indent=2))


def stable_live_inventory(baseline_path, minimum_age_seconds):
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    created = datetime.fromisoformat(baseline["created_at"])
    age = (datetime.now(timezone.utc) - created).total_seconds()
    if age < minimum_age_seconds:
        raise ValueError(
            f"live baseline is only {age:.0f}s old; require {minimum_age_seconds}s"
        )

    current = fetch_live_inventory()
    stable = {}
    for source, records in current.items():
        before = {
            live_fingerprint(record)
            for record in baseline.get("records", {}).get(source, [])
        }
        stable[source] = [
            record
            for record in records
            if live_fingerprint(record) in before
        ]
        for record in stable[source]:
            record["_monitor"] = {
                "first_seen_at": baseline["created_at"],
                "confirmed_at": utc_now_iso(),
            }
    return stable, age


def parse_legacy_key(value):
    match = LEGACY_KEY_RE.match(str(value))
    if not match:
        return None
    tag, event_id, record_type, identity, result, competition = match.groups()
    return {
        "tag": tag,
        "event_id": event_id,
        "type": record_type,
        "identity": identity,
        "result": int(result),
        "competition": competition,
        "old_key": str(value),
    }


def legacy_groups(values):
    groups = []
    rejected = []
    excluded = 0
    for value in values:
        if str(value) in FALSE_LEGACY_KEYS:
            excluded += 1
            continue
        parsed = parse_legacy_key(value)
        if parsed is None:
            rejected.append(str(value))
            continue
        base = (
            parsed["tag"],
            parsed["event_id"],
            parsed["type"],
            parsed["result"],
            parsed["competition"],
        )
        previous = groups[-1] if groups else None
        identities = previous["identities"] if previous else []
        complements_previous = (
            previous is not None
            and previous["base"] == base
            and len(identities) == 1
            and identities[0].startswith("name-") != parsed["identity"].startswith("name-")
        )
        if complements_previous:
            previous["identities"].append(parsed["identity"])
            previous["old_keys"].append(parsed["old_key"])
        else:
            groups.append({
                "base": base,
                "identities": [parsed["identity"]],
                "old_keys": [parsed["old_key"]],
            })
    return groups, rejected, excluded


def legacy_group_record(group, target_key):
    tag, event_id, record_type, value, competition = group["base"]
    person_id = next(
        (identity for identity in group["identities"] if not identity.startswith("name-")),
        "",
    )
    country = target_key.upper() if tag == "NR" and target_key in {"si", "hr"} else ""
    aliases = [
        f"record:{event_id}:{record_type}:{identity}:{value}:{competition}"
        for identity in group["identities"]
    ]
    return {
        "type": record_type,
        "tag": tag,
        "attemptResult": value,
        "_migration_aliases": aliases,
        "result": {
            "attempts": [],
            "person": {
                "name": None,
                "wcaId": person_id,
                "country": {"iso2": country, "name": country},
            },
            "round": {
                "id": None,
                "competitionEvent": {
                    "event": {"id": event_id, "name": event_id},
                    "competition": {
                        "id": competition,
                        "wcaId": competition,
                        "name": None,
                    },
                },
            },
        },
    }


def normalize_pending(value):
    if not isinstance(value, dict):
        return {}
    return {
        str(target): (
            copy.deepcopy(records)
            if isinstance(records, dict)
            else {str(record): {} for record in records}
            if isinstance(records, list)
            else {}
        )
        for target, records in value.items()
    }


def build_slot_data(data, targets, official, stable_live):
    slots = empty_record_slots()
    rejected = []
    excluded = 0
    dedupe = data.get("records_dedupe", {})
    if isinstance(dedupe, list):
        dedupe = {"si": dedupe}
    if not isinstance(dedupe, dict):
        dedupe = {}

    for target_key, values in dedupe.items():
        groups, target_rejected, target_excluded = legacy_groups(
            values if isinstance(values, list) else []
        )
        rejected.extend(target_rejected)
        excluded += target_excluded
        for group in groups:
            record = legacy_group_record(group, str(target_key))
            delivery = {
                str(target_key): {
                    "announced_as": normalized_tag(record),
                    "source": None,
                    "sent_at": None,
                    "message_id": None,
                },
            }
            seed_record(slots, record, deliveries=delivery, source=None)

    for record in official:
        seed_record(
            slots,
            record,
            deliveries=baseline_deliveries(record, targets, "wca_official"),
            source="wca_official",
            current=True,
        )

    for source, records in stable_live.items():
        for record in records:
            seed_record(
                slots,
                record,
                deliveries=baseline_deliveries(record, targets, source),
                source=source,
                current=True,
            )

    migrated = copy.deepcopy(data)
    migrated.pop("records_dedupe", None)
    migrated["record_storage_version"] = RECORD_STORAGE_VERSION
    migrated["record_slots"] = slots
    migrated["records_pending"] = normalize_pending(data.get("records_pending"))
    return migrated, rejected, excluded


def record_summary(record):
    result = record["result"]
    competition_event = result["round"]["competitionEvent"]
    return {
        "tag": normalized_tag(record),
        "event": competition_event["event"]["id"],
        "type": record["type"],
        "person": result["person"].get("wcaId") or result["person"].get("name"),
        "result": record["attemptResult"],
        "competition": competition_event["competition"].get("wcaId"),
    }


def summary(
    data,
    rejected,
    excluded,
    official,
    stable_live,
    baseline_age,
    old_hash,
):
    slots = data["record_slots"]
    entries = sum(len(history) for history in slots.values())
    current = sum(
        1
        for history in slots.values()
        for entry in history
        if entry.get("current") is True
    )
    return {
        "current_data_hash": old_hash,
        "project_ref": project_ref(),
        "slot_count": len(slots),
        "history_entries_across_slots": entries,
        "current_entries_across_slots": current,
        "nonempty_slots": sum(bool(history) for history in slots.values()),
        "official_records": len(official),
        "stable_live": {
            key: [record_summary(record) for record in value]
            for key, value in stable_live.items()
        },
        "live_baseline_age_seconds": round(baseline_age),
        "known_false_legacy_keys_excluded": excluded,
        "unparsed_legacy_keys": rejected,
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-live-baseline", type=Path)
    parser.add_argument("--live-baseline", type=Path)
    parser.add_argument(
        "--legacy-backup",
        type=Path,
        help="Rebuild an already-migrated test row from its pre-v2 backup.",
    )
    parser.add_argument("--minimum-age-seconds", type=int, default=180)
    parser.add_argument("--apply-test", action="store_true")
    parser.add_argument("--confirm-compatible-runtime", action="store_true")
    parser.add_argument("--expected-hash")
    parser.add_argument("--expected-project-ref")
    parser.add_argument("--backup-dir", type=Path, default=Path("/tmp"))
    return parser.parse_args()


def main():
    args = parse_args()
    if args.capture_live_baseline:
        capture_baseline(args.capture_live_baseline)
        return
    if not args.live_baseline:
        raise SystemExit("--live-baseline is required for plan/apply")

    source_row = db.load_second_table_idd(4)
    config_row = db.load_second_table_idd(3)
    current_data = source_row.get("data")
    if not isinstance(current_data, dict):
        raise SystemExit("vars.id=4 data is not an object")
    source_data = current_data
    if current_data.get("record_storage_version") == RECORD_STORAGE_VERSION:
        if not args.legacy_backup:
            raise SystemExit("vars.id=4 is already using record slot storage v2")
        backup_row = json.loads(args.legacy_backup.read_text(encoding="utf-8"))
        source_data = backup_row.get("data")
        if not isinstance(source_data, dict) or "records_dedupe" not in source_data:
            raise SystemExit("--legacy-backup does not contain pre-v2 vars.id=4 data")
    targets = config_row.get("data", {}).get("records_targets", [])
    if not isinstance(targets, list):
        raise SystemExit("vars.id=3 records_targets is not a list")

    old_hash = canonical_hash(current_data)
    official = fetch_official_records()
    stable_live, baseline_age = stable_live_inventory(
        args.live_baseline,
        args.minimum_age_seconds,
    )
    migrated, rejected, excluded = build_slot_data(
        source_data,
        targets,
        official,
        stable_live,
    )
    report = summary(
        migrated,
        rejected,
        excluded,
        official,
        stable_live,
        baseline_age,
        old_hash,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if rejected:
        raise SystemExit("refusing apply: unparsed legacy keys")
    if not args.apply_test:
        return
    if not args.confirm_compatible_runtime:
        raise SystemExit(
            "refusing apply: deploy v2-compatible code or stop every bot process, "
            "then pass --confirm-compatible-runtime"
        )
    if args.expected_hash != old_hash:
        raise SystemExit("refusing apply: --expected-hash does not match current data")
    if args.expected_project_ref != project_ref():
        raise SystemExit("refusing apply: --expected-project-ref does not match SUPA_URL")

    args.backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = args.backup_dir / (
        "cubedbot-vars-4-before-record-slots-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    backup_path.write_text(
        json.dumps(source_row, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    source_row["data"] = migrated
    db.save_second_table_idd(source_row)
    saved = db.load_second_table_idd(4)
    if saved.get("data") != migrated:
        raise SystemExit(
            f"save readback mismatch; inspect backup {backup_path}"
        )
    print(json.dumps({
        "applied": True,
        "backup": str(backup_path),
        "saved_data_hash": canonical_hash(saved["data"]),
    }, indent=2))


if __name__ == "__main__":
    main()
