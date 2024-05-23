import discord
from discord.ext import commands
import requests, json
from datetime import datetime as dt
import datetime

import src.db as db
from src.hardstorage import * 

import src.wca_function as wca_function


def max_len_in_collum(data):
    return [max(len(str(element)) for element in column) for column in zip(*data)]


class userfinderCog(commands.Cog, name="userfinder command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="userfinder", usage="(member:mention) OR (wca id:str)", description="Displays wca profile of user/wca id")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def userFinder(
        self, ctx: discord.ApplicationContext,
        nationality:str,
        start_data=str,
        end_data=str,
        ):
        
        q = discord.Embed(title="Finder")
        
        all_competitions = wca_function.list_of_events_from()
        for competition in all_competitions:
            c = wca_function.competitors_in_comp(competition)
            print(c)
            
            
            
        q.add_field(name="Stats",value=f"Scaned {len(all_competitions)} competitions")
        await ctx.send(embed=q)
            
            
            
        
        


def setup(bot: commands.Bot):
    bot.add_cog(userfinderCog(bot))
