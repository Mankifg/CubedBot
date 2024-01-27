import discord
from discord.ext import commands
import requests, json


class linksCog(commands.Cog, name="links command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="links", usage="", description="Some links for bot"
    )
    async def links(self, ctx):
        q = discord.Embed(title="Links", color=discord.Color.blue())
        q.add_field(
            name="Github Page",
            value="https://github.com/Mankifg/CubedBot",
            inline=False,
        )
    

        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(linksCog(bot))
