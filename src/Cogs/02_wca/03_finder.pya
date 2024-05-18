import discord
from discord.ext import commands
import requests, json

import src.db as db
import src.hardstorage
import src.wca_functions as wca_functions
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

    @discord.command(name="finder", usage="", description="no")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def finder(
        self,
        ctx: discord.ApplicationContext,
        dan: int,
        mesec: discord.Option(choices=meseci),
        leto: int,
        drzava,
    ):

        comps = wca_functions.find_by_date(dan, mesec, leto)

        await ctx.send("finder")


def setup(bot: commands.Bot):
    bot.add_cog(finderCog(bot))
