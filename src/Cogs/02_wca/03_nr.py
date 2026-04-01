import asyncio

import discord
from discord.ext import commands
import requests

import src.functions as functions
import src.hardstorage as hs
import src.wca_function as wca_function
from src.guild_access import primary_guild_id, croatian_guild_id


RAW_RANK_BASE = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/rank"
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
    "222",
    "333",
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
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
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


def _rank_url(country_iso2, rank_type, event_id):
    return f"{RAW_RANK_BASE}/{country_iso2}/{rank_type}/{event_id}.json"


def _format_best_value(event_id, rank_type, best_raw):
    if event_id == "333fm" and rank_type == "average":
        return f"{best_raw / 100:.2f}"
    return functions.convert_to_human_frm(best_raw, event_id)


def _fetch_rank_record(country_iso2, rank_type, event_id, person_cache):
    url = _rank_url(country_iso2, rank_type, event_id)
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    if response.status_code == 404:
        return None, url
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not items:
        return None, url

    best = items[0]
    person_id = best.get("personId", "")

    if person_id not in person_cache:
        person_cache[person_id] = wca_function.get_wca_data(person_id)

    person_data = person_cache.get(person_id) or {}
    person_name = person_data.get("name") or person_id

    return {
        "event_id": event_id,
        "event_name": hs.DICTIONARY.get(event_id, event_id),
        "rank_type": rank_type,
        "best_raw": best.get("best", 0),
        "best": _format_best_value(event_id, rank_type, best.get("best", 0)),
        "person_id": person_id,
        "person_name": person_name,
        "person_url": f"https://www.worldcubeassociation.org/persons/{person_id}" if person_id else None,
        "rank": best.get("rank", {}),
        "source_url": url,
    }, url


def _format_record_line(record):
    if record is None:
        return "-"

    holder = record.get("person_name") or record.get("person_id") or "Unknown"
    person_url = record.get("person_url")
    if person_url:
        holder = f"[{holder}]({person_url})"

    return f"`{record['best']}` — {holder}"


def _event_display_name(event_id):
    return WCA_EVENT_NAMES.get(event_id, hs.DICTIONARY.get(event_id, event_id))


def _build_description(records):
    lines = []
    for row in records:
        event_label = f"**{_event_display_name(row['event_id'])}**"
        average_label = "Mean" if row["event_id"] in MEAN_LABEL_EVENTS else "Average"
        if row["single"] is not None and row["average"] is not None:
            single_line = _format_record_line(row["single"])
            average_line = _format_record_line(row["average"])
            lines.append(f"{event_label}\nSingle: {single_line}\n{average_label}: {average_line}")
        elif row["single"] is not None:
            lines.append(f"{event_label}\nSingle: {_format_record_line(row['single'])}")
        elif row["average"] is not None:
            lines.append(f"{event_label}\n{average_label}: {_format_record_line(row['average'])}")

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
        required=False,
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def nr(self, ctx, event="All"):
        await ctx.defer()

        country_iso2, country_name = _default_country_for_guild(getattr(ctx, "guild_id", None))

        selected_event = EVENT_LABEL_TO_ID.get(event, None)
        if event in EVENT_GROUPS:
            event_ids = EVENT_GROUPS[event]
        else:
            event_ids = [selected_event] if selected_event else ALL_EVENT_ORDER
        person_cache = {}

        try:
            records = []
            source_urls = []
            for event_id in event_ids:
                single_record = None
                average_record = None

                single_record, single_url = await asyncio.to_thread(
                    _fetch_rank_record, country_iso2, "single", event_id, person_cache
                )
                source_urls.append(single_url)

                average_record, average_url = await asyncio.to_thread(
                    _fetch_rank_record, country_iso2, "average", event_id, person_cache
                )
                source_urls.append(average_url)

                if single_record or average_record:
                    records.append(
                        {
                            "event_id": event_id,
                            "event_name": _event_display_name(event_id),
                            "single": single_record,
                            "average": average_record,
                        }
                    )
        except Exception as exc:
            q = discord.Embed(
                title="Could not fetch national records",
                description=(
                    "The national-records data source could not be loaded right now."
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

        q = discord.Embed(
            title=f"National Records — {country_name}",
            description=description[:4000],
            color=discord.Colour.blue(),
        )
        await ctx.respond(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
