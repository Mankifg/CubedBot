import discord
from discord.ext import commands
import requests, json

import db

import wca_functions


class nrCog(commands.Cog, name="nr command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="nr", usage="(wca id:str)", description="Changes your wca id assciated with your discord username")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def nr(self, ctx,):
        pass
        # todo


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
