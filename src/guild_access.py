import discord

import src.db as db


def _load_guild_config():
    row = db.load_second_table_idd(8)
    data = row.get("data")
    if isinstance(data, dict):
        return data
    return {}


def primary_guild_id():
    data = _load_guild_config()
    guild_id = data.get("primary_guild_id")
    try:
        return int(guild_id)
    except (TypeError, ValueError):
        return None


def croatian_guild_id():
    data = _load_guild_config()
    guild_id = data.get("croatian_guild_id")
    try:
        return int(guild_id)
    except (TypeError, ValueError):
        return None


def is_primary_guild(guild_id):
    return guild_id == primary_guild_id()


def primary_guild_ids():
    guild_id = primary_guild_id()
    if guild_id is None:
        return []
    return [guild_id]


def both_guild_ids():
    guild_ids = []
    for guild_id in (primary_guild_id(), croatian_guild_id()):
        if guild_id is not None and guild_id not in guild_ids:
            guild_ids.append(guild_id)
    return guild_ids


async def ensure_primary_guild(ctx, bot):
    if is_primary_guild(getattr(ctx, "guild_id", None)):
        return True

    q = discord.Embed(
        title="Command unavailable here",
        description="This command is only available in the Slovenian server.",
        color=discord.Colour.orange(),
    )
    await ctx.respond(embed=q, ephemeral=True)
    return False
