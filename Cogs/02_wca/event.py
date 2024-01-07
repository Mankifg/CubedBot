import discord
from discord.ext import commands
import requests, json

import db
from hardstorage import * 
import wca_functions
import functions

EVENTS_ENDPOINT = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{}.json"



class eventCog(commands.Cog, name="event command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="event", usage="", description="")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def event(self, ctx,):
        ...
        

def setup(bot: commands.Bot):
    bot.add_cog(eventCog(bot))
