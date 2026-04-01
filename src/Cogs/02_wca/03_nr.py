import asyncio
from urllib.parse import quote

import discord
from discord.ext import commands
import requests

import src.functions as functions
import src.hardstorage as hs
from src.guild_access import primary_guild_id, croatian_guild_id


RECORDS_PAGE_URL = "https://www.worldcubeassociation.org/results/records"
EVENT_LABEL_TO_ID = {
    "All": None,
    "222": "222",
    "333": "333",
    "444": "444",
    "555": "555",
    "666": "666",
    "777": "777",
    "3BLD": "333bf",
    "FMC": "333fm",
    "OH": "333oh",
    "Clock": "clock",
    "Minx": "minx",
    "Pyra": "pyram",
    "Skewb": "skewb",
    "Sq1": "sq1",
    "4BLD": "444bf",
    "5BLD": "555bf",
    "MBLD": "333mbf",
    "3x3 Variants": None,
    "BLD Variants": None,
    "NxN Cubes": None,
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
MEAN_LABEL_EVENTS = {"333fm", "444bf", "555bf", "666", "777"}
ALL_EVENT_ORDER = [
    "333",
    "222",
    "444",
    "555",
    "666",
    "777",
    "333bf",
    "333fm",
    "333oh",
    "clock",
    "minx",
    "pyram",
    "skewb",
    "sq1",
    "444bf",
    "555bf",
    "333mbf",
]
EVENT_GROUPS = {
    "All": ALL_EVENT_ORDER,
    "BLD Variants": ["333bf", "444bf", "555bf", "333mbf"],
    "3x3 Variants": ["333", "333oh", "333bf", "333fm"],
    "NxN Cubes": ["222", "333", "444", "555", "666", "777"],
}

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

EVENT_CHOICES = list(EVENT_LABEL_TO_ID.keys())


def _nr_guild_ids():
    guild_ids = []
    for guild_id in (primary_guild_id(), croatian_guild_id()):
        if guild_id is not None and guild_id not in guild_ids:
            guild_ids.append(guild_id)
    return guild_ids


def _default_country_for_guild(guild_id):
    if guild_id == croatian_guild_id():
        return ("HR", "Croatia")
    if guild_id == primary_guild_id():
        return ("SI", "Slovenia")
    return ("SI", "Slovenia")


def _records_url(country_name):
    return f"{RECORDS_PAGE_URL}?region={quote(country_name)}&show=mixed"


def _format_best_value(event_id, rank_type, value):
    if event_id == "333fm" and rank_type == "average":
        return f"{value / 100:.2f}"
    return functions.convert_to_human_frm(value, event_id)


def _record_from_row(row):
    event_id = row.get("event_id")
    rank_type = row.get("type")
    value = row.get("value")
    if not event_id or rank_type not in {"single", "average"} or value is None:
        return None

    person_id = row.get("person_id", "")
    return {
        "event_id": event_id,
        "event_name": _event_display_name(event_id),
        "rank_type": rank_type,
        "best_raw": value,
        "best": _format_best_value(event_id, rank_type, value),
        "person_id": person_id,
        "person_name": row.get("person_name") or person_id or "Unknown",
        "person_url": f"https://www.worldcubeassociation.org/persons/{person_id}" if person_id else None,
        "competition_id": row.get("competition_id"),
        "competition_name": row.get("competition_name"),
        "competition_url": (
            f"https://www.worldcubeassociation.org/competitions/{row['competition_id']}"
            if row.get("competition_id")
            else None
        ),
        "attempts": row.get("attempts") or [],
        "value": value,
        "source_updated_at": row.get("updated_at"),
    }


def _dedupe_records_by_person(records):
    deduped = []
    seen = set()

    for record in records:
        if record is None:
            continue
        person_id = record.get("person_id") or record.get("person_name")
        if person_id in seen:
            continue
        seen.add(person_id)
        deduped.append(record)

    return deduped


def _fetch_country_records(country_name, event_ids):
    url = _records_url(country_name)
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("rows", []) if isinstance(payload, dict) else []

    grouped = {}
    for row in rows:
        event_id = row.get("event_id")
        rank_type = row.get("type")
        if event_id not in event_ids or rank_type not in {"single", "average"}:
            continue
        grouped.setdefault(event_id, {"single": [], "average": []})
        grouped[event_id][rank_type].append(_record_from_row(row))

    records = []
    for event_id in event_ids:
        event_rows = grouped.get(event_id)
        if not event_rows:
            continue
        single_records = _dedupe_records_by_person(event_rows["single"])
        average_records = _dedupe_records_by_person(event_rows["average"])
        if single_records or average_records:
            records.append(
                {
                    "event_id": event_id,
                    "event_name": _event_display_name(event_id),
                    "single": single_records,
                    "average": average_records,
                }
            )

    return records, url


def _format_record_line(record):
    if record is None:
        return "-"

    holder = record.get("person_name") or record.get("person_id") or "Unknown"
    person_url = record.get("person_url")
    if person_url:
        holder = f"[{holder}]({person_url})"

    return f"`{record['best']}` — {holder}"


def _format_record_lines(records):
    if not records:
        return "-"
    return "\n".join(_format_record_line(record) for record in records)


def _event_display_name(event_id):
    return WCA_EVENT_NAMES.get(event_id, hs.DICTIONARY.get(event_id, event_id))


def _build_description(records):
    lines = []
    for row in records:
        event_label = f"**{_event_display_name(row['event_id'])}**"
        average_label = "Mean" if row["event_id"] in MEAN_LABEL_EVENTS else "Average"
        if row["single"] and row["average"]:
            single_line = _format_record_lines(row["single"])
            average_line = _format_record_lines(row["average"])
            lines.append(f"{event_label}\nSingle: {single_line}\n{average_label}: {average_line}")
        elif row["single"]:
            lines.append(f"{event_label}\nSingle: {_format_record_lines(row['single'])}")
        elif row["average"]:
            lines.append(f"{event_label}\n{average_label}: {_format_record_lines(row['average'])}")

    return "\n\n".join(lines)


class nrCog(commands.Cog, name="national records command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="nr",
        description="Show current national records.",
        guild_ids=_nr_guild_ids(),
    )
    @discord.option(
        name="event",
        description="Choose WCA event.",
        choices=EVENT_CHOICES,
        required=True,
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def nr(self, ctx, event):
        await ctx.defer()

        _country_iso2, country_name = _default_country_for_guild(getattr(ctx, "guild_id", None))

        selected_event = EVENT_LABEL_TO_ID.get(event, None)
        if event in EVENT_GROUPS:
            event_ids = EVENT_GROUPS[event]
        else:
            event_ids = [selected_event] if selected_event else ALL_EVENT_ORDER

        try:
            records, source_url = await asyncio.to_thread(
                _fetch_country_records, country_name, event_ids
            )
        except Exception as exc:
            q = discord.Embed(
                title="Could not fetch national records",
                description=(
                    "The national-records data source could not be loaded right now.\n"
                    f"[Open records page]({_records_url(country_name)})"
                ),
                color=discord.Colour.red(),
            )
            q.set_footer(text=str(exc)[:200])
            await ctx.respond(embed=q)
            return

        if not records:
            q = discord.Embed(
                title="No records found",
                description="No matching records were found for that filter.",
                color=discord.Colour.orange(),
            )
            await ctx.respond(embed=q)
            return

        description = _build_description(records)
        if not description:
            q = discord.Embed(
                title="No records found",
                description="No matching records were found for that filter.",
                color=discord.Colour.orange(),
            )
            await ctx.respond(embed=q)
            return

        bundle_header = f"**{event}**\n\n" if event in EVENT_GROUPS and event != "All" else ""
        q = discord.Embed(
            title=f"National Records — {country_name}",
            description=f"{bundle_header}{description}"[:4000],
            color=discord.Colour.blue(),
        )
        await ctx.respond(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
