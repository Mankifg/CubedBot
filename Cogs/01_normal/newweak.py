import discord
from discord.ext import commands
import requests, json

from datetime import datetime as dt

import db


class newweakCog(commands.Cog, name="newweak command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="newweak",
        usage="",
        description="Gives a newweak for essentially everything.",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def newweak(self, ctx, weak: str):
        
        current_weak = db.load_second_table_iddata(1)  # weak
        
        current_weak = current_weak["data"]
        
        print(current_weak)

        current_weak = weak


def setup(bot: commands.Bot):
    bot.add_cog(newweakCog(bot))
