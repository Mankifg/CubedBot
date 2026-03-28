import discord


SLOVENIAN_GUILD_ID = 927949850996277298
CROATIAN_GUILD_ID = 1160626532516106310


def is_primary_guild(guild_id):
    return guild_id == SLOVENIAN_GUILD_ID


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
