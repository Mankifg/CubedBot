import discord
from discord.ext import commands
import requests, json

import src.db as db
import src.hardstorage
import src.wca_function as wca_function
import src.functions as functions

from datetime import datetime as dt

meseci = [
    "1 January",
    "2 February",
    "3 March",
    "4 April",
    "5 May",
    "6 June",
    "7 July",
    "8 August",
    "9 September",
    "10 October",
    "11 November",
    "12 December",
]


class finderCog(commands.Cog, name="finder command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="finder", usage="", description="WIP")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def finder(
        self,
        ctx: discord.ApplicationContext,
        dan: int,
        mesec: discord.Option(choices=meseci),
        leto: int,
        drzava,
    ):

        #comps = wca_function.find_by_date(dan, mesec, leto)

        await ctx.send("finder")
        q = discord.Embed(title="<@650756055390879757>")
        q.add_field(name="a",value="<@650756055390879757>")
        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(finderCog(bot))
