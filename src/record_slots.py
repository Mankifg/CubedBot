import copy
import unicodedata
from datetime import datetime, timezone


RECORD_STORAGE_VERSION = 2
TRACKED_COUNTRIES = {"SI", "HR"}
EUROPEAN_ISO2 = {
    "AD", "AL", "AM", "AT", "AZ", "BA", "BE", "BG", "BY", "CH", "CY",
    "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GB", "GE", "GR", "HR",
    "HU", "IE", "IL", "IS", "IT", "LI", "LT", "LU", "LV", "MC", "MD",
    "ME", "MK", "MT", "NL", "NO", "PL", "PT", "RO", "RS", "RU", "SE",
    "SI", "SK", "SM", "TR", "UA", "VA", "XE", "XK",
}
EVENT_IDS = (
    "222", "333", "444", "555", "666", "777", "333bf", "333fm",
    "333mbf", "333oh", "clock", "minx", "pyram", "skewb", "sq1", "fto",
    "444bf", "555bf",
)
RECORD_TYPES_BY_EVENT = {
    event_id: ("single",) if event_id == "333mbf" else ("single", "average")
    for event_id in EVENT_IDS
}
LEVEL_RANK = {"NR": 1, "ER": 2, "WR": 3}


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_text(value):
    if value is None:
        return "unknown"
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(
        char.lower()
        for char in text
        if char.isascii() and char.isalnum()
    ) or "unknown"


def slot_key(level, event_id, record_type, country_iso2=None):
    level = str(level).upper()
    if level == "NR":
        return f"NR:{str(country_iso2).upper()}:{event_id}:{record_type}"
    return f"{level}:{event_id}:{record_type}"


def all_slot_keys():
    keys = []
    for event_id in EVENT_IDS:
        for record_type in RECORD_TYPES_BY_EVENT[event_id]:
            keys.extend((
                slot_key("WR", event_id, record_type),
                slot_key("ER", event_id, record_type),
                slot_key("NR", event_id, record_type, "SI"),
                slot_key("NR", event_id, record_type, "HR"),
            ))
    return keys


def empty_record_slots():
    return {key: [] for key in all_slot_keys()}


def is_slot_storage(data):
    return (
        isinstance(data, dict)
        and data.get("record_storage_version") == RECORD_STORAGE_VERSION
        and isinstance(data.get("record_slots"), dict)
    )


def ensure_record_slots(data):
    if not isinstance(data, dict):
        raise ValueError("record data must be an object")
    slots = data.get("record_slots")
    if not isinstance(slots, dict):
        slots = {}
        data["record_slots"] = slots
    for key in all_slot_keys():
        if not isinstance(slots.get(key), list):
            slots[key] = []
    data["record_storage_version"] = RECORD_STORAGE_VERSION
    return slots


def _record_parts(record):
    result = record["result"]
    person = result["person"]
    round_obj = result["round"]
    competition_event = round_obj["competitionEvent"]
    competition = competition_event["competition"]
    return result, person, round_obj, competition_event, competition


def record_aliases(record):
    _result, person, _round, competition_event, competition = _record_parts(record)
    event_id = competition_event["event"]["id"]
    record_type = record["type"]
    value = record["attemptResult"]
    competition_key = canonical_text(
        competition.get("wcaId") or competition.get("name")
    )
    identities = []
    wca_id = str(person.get("wcaId") or "").strip()
    if wca_id:
        identities.append(wca_id)
    person_name = str(person.get("name") or "").strip()
    if person_name:
        identities.append(f"name-{canonical_text(person_name)}")
    if not identities:
        identities.append("unknown")
    return [
        f"record:{event_id}:{record_type}:{identity}:{value}:{competition_key}"
        for identity in identities
    ]


def record_primary_id(record):
    return record_aliases(record)[0]


def slots_affected_by_record(record):
    _result, person, _round, competition_event, _competition = _record_parts(record)
    event_id = competition_event["event"]["id"]
    record_type = record["type"]
    tag = str(record.get("tag") or "").upper()
    if tag == "CR":
        tag = "ER"
    country_iso2 = str(person.get("country", {}).get("iso2") or "").upper()

    keys = []
    if tag == "WR":
        keys.append(slot_key("WR", event_id, record_type))
        if country_iso2 in EUROPEAN_ISO2:
            keys.append(slot_key("ER", event_id, record_type))
        if country_iso2 in TRACKED_COUNTRIES:
            keys.append(slot_key("NR", event_id, record_type, country_iso2))
    elif tag == "ER":
        keys.append(slot_key("ER", event_id, record_type))
        if country_iso2 in TRACKED_COUNTRIES:
            keys.append(slot_key("NR", event_id, record_type, country_iso2))
    elif tag == "NR" and country_iso2 in TRACKED_COUNTRIES:
        keys.append(slot_key("NR", event_id, record_type, country_iso2))
    return keys


def slots_checked_for_record(record):
    _result, person, _round, competition_event, _competition = _record_parts(record)
    event_id = competition_event["event"]["id"]
    record_type = record["type"]
    tag = str(record.get("tag") or "").upper()
    if tag == "CR":
        tag = "ER"
    country_iso2 = str(person.get("country", {}).get("iso2") or "").upper()

    if tag == "WR":
        return [slot_key("WR", event_id, record_type)]
    if tag == "ER":
        return [
            slot_key("ER", event_id, record_type),
            slot_key("WR", event_id, record_type),
        ]
    if tag == "NR" and country_iso2 in TRACKED_COUNTRIES:
        return [
            slot_key("NR", event_id, record_type, country_iso2),
            slot_key("ER", event_id, record_type),
            slot_key("WR", event_id, record_type),
        ]
    return []


def _matching_entry(slot_entries, aliases):
    alias_set = set(aliases)
    for entry in slot_entries:
        if not isinstance(entry, dict):
            continue
        entry_aliases = entry.get("aliases")
        if not isinstance(entry_aliases, list):
            entry_aliases = [entry.get("record_id")]
        if alias_set & {str(alias) for alias in entry_aliases if alias}:
            return entry
    return None


def already_delivered(slots, target_key, record):
    aliases = record_aliases(record)
    for key in slots_checked_for_record(record):
        entry = _matching_entry(slots.get(key, []), aliases)
        if not entry:
            continue
        deliveries = entry.get("deliveries")
        if isinstance(deliveries, dict) and target_key in deliveries:
            return True
    return False


def _new_entry(record, source):
    result, person, round_obj, competition_event, competition = _record_parts(record)
    monitor = record.get("_monitor") if isinstance(record.get("_monitor"), dict) else {}
    aliases = record_aliases(record)
    extra_aliases = record.get("_migration_aliases")
    if isinstance(extra_aliases, list):
        for alias in extra_aliases:
            if alias and alias not in aliases:
                aliases.append(str(alias))
    return {
        "record_id": aliases[0],
        "aliases": aliases,
        "person_id": str(person.get("wcaId") or "") or None,
        "person_name": person.get("name"),
        "country_iso2": str(person.get("country", {}).get("iso2") or "").upper() or None,
        "event_id": competition_event["event"]["id"],
        "type": record["type"],
        "result": record["attemptResult"],
        "competition_id": competition.get("wcaId"),
        "competition_name": competition.get("name"),
        "round_id": round_obj.get("id"),
        "highest_tag": str(record.get("tag") or "").upper().replace("CR", "ER"),
        "sources": [source] if source else [],
        "first_seen_at": monitor.get("first_seen_at"),
        "confirmed_at": monitor.get("confirmed_at"),
        "current": False,
        "deliveries": {},
    }


def _merge_entry(existing, incoming):
    aliases = list(existing.get("aliases") or [])
    for alias in incoming.get("aliases") or []:
        if alias not in aliases:
            aliases.append(alias)
    existing["aliases"] = aliases
    if not existing.get("record_id"):
        existing["record_id"] = incoming.get("record_id")
    for field in (
        "person_id", "person_name", "country_iso2", "event_id", "type",
        "result", "competition_id", "competition_name", "round_id",
    ):
        if incoming.get(field) is not None:
            existing[field] = incoming[field]
    for field in ("first_seen_at", "confirmed_at"):
        if existing.get(field) is None and incoming.get(field) is not None:
            existing[field] = incoming[field]
    old_tag = str(existing.get("highest_tag") or "")
    new_tag = str(incoming.get("highest_tag") or "")
    if LEVEL_RANK.get(new_tag, 0) > LEVEL_RANK.get(old_tag, 0):
        existing["highest_tag"] = new_tag
    sources = list(existing.get("sources") or [])
    for source in incoming.get("sources") or []:
        if source and source not in sources:
            sources.append(source)
    existing["sources"] = sources


def _entry_aliases(entry):
    aliases = entry.get("aliases")
    if isinstance(aliases, list):
        return {str(alias) for alias in aliases if alias}
    record_id = entry.get("record_id")
    return {str(record_id)} if record_id else set()


def _set_current(entries, entry):
    """Mark a tagged achievement current without erasing equal-result ties."""
    value = entry.get("result")
    if not isinstance(value, int) or value <= 0:
        return

    current_entries = [
        item
        for item in entries
        if isinstance(item, dict)
        and item.get("current") is True
        and isinstance(item.get("result"), int)
        and item["result"] > 0
    ]
    if not current_entries:
        entry["current"] = True
        return

    current_value = min(item["result"] for item in current_entries)
    if value < current_value:
        for item in current_entries:
            item["current"] = False
        entry["current"] = True
    elif value == current_value:
        entry["current"] = True


def _matching_entries(slots, aliases):
    alias_set = set(aliases)
    matches = []
    for entries in slots.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and alias_set & _entry_aliases(entry):
                matches.append(entry)
    return matches


def _merge_deliveries(existing, incoming):
    for target_key, incoming_delivery in incoming.items():
        if not isinstance(incoming_delivery, dict):
            continue
        existing_delivery = existing.get(target_key)
        if not isinstance(existing_delivery, dict):
            existing[target_key] = copy.deepcopy(incoming_delivery)
            continue
        old_tag = str(existing_delivery.get("announced_as") or "")
        new_tag = str(incoming_delivery.get("announced_as") or "")
        if LEVEL_RANK.get(new_tag, 0) > LEVEL_RANK.get(old_tag, 0):
            existing[target_key] = copy.deepcopy(incoming_delivery)
            continue
        if LEVEL_RANK.get(new_tag, 0) == LEVEL_RANK.get(old_tag, 0):
            for field, value in incoming_delivery.items():
                if existing_delivery.get(field) is None and value is not None:
                    existing_delivery[field] = copy.deepcopy(value)


def record_delivery(slots, target_key, record, source, sent_at=None, message_id=None):
    affected = slots_affected_by_record(record)
    if not affected:
        return False
    incoming = _new_entry(record, source)
    delivery = {
        "announced_as": str(record.get("tag") or "").upper().replace("CR", "ER"),
        "source": source,
        "sent_at": sent_at or utc_now_iso(),
        "message_id": str(message_id) if message_id is not None else None,
    }
    matching_copies = _matching_entries(slots, incoming["aliases"])
    for existing in matching_copies:
        _merge_entry(existing, incoming)
        deliveries = existing.get("deliveries")
        if not isinstance(deliveries, dict):
            deliveries = {}
            existing["deliveries"] = deliveries
        _merge_deliveries(deliveries, {target_key: delivery})

    for key in affected:
        entries = slots.setdefault(key, [])
        existing = _matching_entry(entries, incoming["aliases"])
        if existing is None:
            existing = copy.deepcopy(incoming)
            entries.append(existing)
        else:
            _merge_entry(existing, incoming)
        deliveries = existing.get("deliveries")
        if not isinstance(deliveries, dict):
            deliveries = {}
            existing["deliveries"] = deliveries
        _merge_deliveries(deliveries, {target_key: delivery})
        _set_current(entries, existing)
    return True


def seed_record(
    slots,
    record,
    deliveries=None,
    source="migration",
    current=False,
):
    affected = slots_affected_by_record(record)
    if not affected:
        return False
    incoming = _new_entry(record, source)
    incoming["deliveries"] = copy.deepcopy(deliveries or {})
    matching_copies = _matching_entries(slots, incoming["aliases"])
    aggregate_deliveries = {}
    highest_tag = incoming["highest_tag"]
    for existing in matching_copies:
        existing_tag = str(existing.get("highest_tag") or "")
        if LEVEL_RANK.get(existing_tag, 0) > LEVEL_RANK.get(highest_tag, 0):
            highest_tag = existing_tag
        existing_deliveries = existing.get("deliveries")
        if isinstance(existing_deliveries, dict):
            _merge_deliveries(aggregate_deliveries, existing_deliveries)
    _merge_deliveries(aggregate_deliveries, incoming["deliveries"])
    incoming["highest_tag"] = highest_tag
    incoming["deliveries"] = aggregate_deliveries

    for existing in matching_copies:
        _merge_entry(existing, incoming)
        existing_deliveries = existing.get("deliveries")
        if not isinstance(existing_deliveries, dict):
            existing_deliveries = {}
            existing["deliveries"] = existing_deliveries
        _merge_deliveries(existing_deliveries, aggregate_deliveries)

    for key in affected:
        entries = slots.setdefault(key, [])
        existing = _matching_entry(entries, incoming["aliases"])
        if existing is None:
            existing = copy.deepcopy(incoming)
            entries.append(existing)
            if current:
                _set_current(entries, existing)
            continue
        _merge_entry(existing, incoming)
        existing_deliveries = existing.get("deliveries")
        if not isinstance(existing_deliveries, dict):
            existing_deliveries = {}
            existing["deliveries"] = existing_deliveries
        _merge_deliveries(existing_deliveries, incoming["deliveries"])
        if current:
            _set_current(entries, existing)
        entries.remove(existing)
        entries.append(existing)
    return True


def merge_record_slots(target_slots, source_slots):
    """Merge append-only histories, preferring source values for known entries."""
    for key in all_slot_keys():
        target_entries = target_slots.setdefault(key, [])
        source_entries = source_slots.get(key, [])
        if not isinstance(source_entries, list):
            continue
        for source_entry in source_entries:
            if not isinstance(source_entry, dict):
                continue
            aliases = _entry_aliases(source_entry)
            target_entry = _matching_entry(target_entries, aliases)
            if target_entry is None:
                target_entries.append(copy.deepcopy(source_entry))
                continue
            _merge_entry(target_entry, source_entry)
            if "current" in source_entry:
                target_entry["current"] = bool(source_entry["current"])
            source_deliveries = source_entry.get("deliveries")
            if isinstance(source_deliveries, dict):
                deliveries = target_entry.get("deliveries")
                if not isinstance(deliveries, dict):
                    deliveries = {}
                    target_entry["deliveries"] = deliveries
                _merge_deliveries(deliveries, source_deliveries)
    return target_slots
