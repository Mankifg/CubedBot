from datetime import date, timedelta


CUBING_CHINA_API_BASE = "https://api.cubing.com"
SUPPORTED_RECORD_TAGS = {"WR", "ER", "NR"}


def active_wca_competitions(competitions, today, grace_days=2):
    """Return live-enabled WCA competitions active in the monitoring window."""
    active = []
    seen_aliases = set()

    for competition in competitions:
        if not isinstance(competition, dict) or not competition.get("live"):
            continue

        alias = str(competition.get("alias") or "").strip()
        wca_id = str(competition.get("wcaCompetitionId") or "").strip()
        if not alias or not wca_id or alias in seen_aliases:
            continue

        try:
            start_date = date.fromisoformat(str(competition.get("startDate")))
            end_date = date.fromisoformat(
                str(competition.get("endDate") or competition.get("startDate"))
            )
        except (TypeError, ValueError):
            continue

        if start_date <= today <= end_date + timedelta(days=grace_days):
            active.append(competition)
            seen_aliases.add(alias)

    return active


def trim_unentered_attempts(attempts):
    attempts = [attempt for attempt in attempts if isinstance(attempt, int)]
    while attempts and attempts[-1] == 0:
        attempts.pop()
    return attempts


def live_result_to_records(result, competition, event_name):
    """Normalize one Cubing China live result into CubedBot record objects."""
    if not isinstance(result, dict) or not isinstance(competition, dict):
        return []

    event_id = str(result.get("eventId") or "").strip()
    competition_alias = str(competition.get("alias") or "").strip()
    competition_id = str(competition.get("wcaCompetitionId") or "").strip()
    if not event_id or not competition_alias or not competition_id:
        return []

    competitor = result.get("competitor")
    if not isinstance(competitor, dict):
        return []

    person_name = str(competitor.get("name") or "").strip()
    local_name = str(competitor.get("localName") or "").strip()
    if local_name and local_name not in person_name:
        person_name = f"{person_name} ({local_name})"
    person_wca_id = str(competitor.get("wcaId") or "").strip()
    country_iso2 = str(competitor.get("regionIso2") or "").strip().upper()
    if not person_name:
        return []

    attempts = trim_unentered_attempts(result.get("attempts") or [])
    round_id = result.get("competitionRoundId")
    if round_id is None:
        round_id = f"{event_id}-r{result.get('roundNumber', 'unknown')}"

    base_result = {
        "attempts": [{"result": attempt} for attempt in attempts],
        "person": {
            "name": person_name,
            "wcaId": person_wca_id,
            "country": {
                "iso2": country_iso2,
                "name": country_iso2,
            },
        },
        "round": {
            "id": round_id,
            "number": result.get("roundNumber"),
            "competitionEvent": {
                "event": {
                    "id": event_id,
                    "name": event_name,
                },
                "competition": {
                    "id": competition_id,
                    "wcaId": competition_id,
                    "name": str(competition.get("name") or competition_id),
                    "cubingChinaAlias": competition_alias,
                },
            },
        },
    }

    records = []
    result_id = result.get("id", "unknown")
    record_specs = (
        ("single", "regionalSingleRecord", "best"),
        ("average", "regionalAverageRecord", "average"),
    )
    for record_type, tag_field, value_field in record_specs:
        value = result.get(value_field)
        tag = str(result.get(tag_field) or "").upper()
        if tag not in SUPPORTED_RECORD_TAGS:
            continue
        if not isinstance(value, int) or value <= 0:
            continue
        records.append({
            "id": f"cubing-china:{result_id}:{record_type}:{value}",
            "type": record_type,
            "tag": tag,
            "attemptResult": value,
            "result": base_result,
        })

    return records
