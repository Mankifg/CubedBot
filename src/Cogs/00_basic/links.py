import discord
from discord.ext import commands
import requests, json
from src.guild_access import ensure_primary_guild, primary_guild_ids


class linksCog(commands.Cog, name="links command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="links", usage="", description="Useful Cubed Bot and WCA links.", guild_ids=primary_guild_ids()
    )
    async def links(self, ctx):
        if not await ensure_primary_guild(ctx, self.bot):
            return
        await ctx.respond("Preparing response...", ephemeral=True)
        q = discord.Embed(title="Links", color=discord.Color.blue())
        q.add_field(
            name="WCA",
            value="[worldcubeassociation.org](https://www.worldcubeassociation.org/)",
            inline=False,
        )
        q.add_field(
            name="WCA Live",
            value="[live.worldcubeassociation.org](https://live.worldcubeassociation.org/)",
            inline=False,
        )
        q.add_field(
            name="Rubik Klub Slovenija",
            value="[rubiks.si](https://www.rubiks.si/)",
            inline=False,
        )
        q.add_field(
            name="Source Code",
            value="[github.com/Mankifg/CubedBot](https://github.com/Mankifg/CubedBot)",
            inline=False,
        )
    

        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(linksCog(bot))
