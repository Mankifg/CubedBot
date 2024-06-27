import discord
from discord.ext import commands
import requests, json

from datetime import datetime as dt
import datetime
from datetime import timedelta

import src.db as db
from src.hardstorage import * 

import src.wca_function as wca_function

COMP_ULR = "https://www.worldcubeassociation.org/competitions/{}/registrations"
NUMBER_OF_DAYS_TO_SEARCH = 7

def max_len_in_collum(data):
    return [max(len(str(element)) for element in column) for column in zip(*data)]

def valid_time(time):
    if time is None:
        return False
    
    try:
        dt.strptime(time, '%Y-%m-%d')
    except ValueError:
        return False
    
    return True


class userfinderCog(commands.Cog, name="userfinder command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="userfinder", usage="(member:mention) OR (wca id:str)", description="Displays wca profile of user/wca id")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def userFinder(
        self, ctx: discord.ApplicationContext,
        nationality:str,
        start_date:str=None,
        end_date:str=None,
        ):
        
        if not valid_time(start_date):
            start_date = dt.now()
        else:
            start_date = dt.strptime(start_date, '%Y-%m-%d')
            
        
        if end_date is None:
            end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)  
        elif end_date.isnumeric():
            end_date = start_date + timedelta(days=int(end_date))
        elif not valid_time(end_date):
            end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)
        else:
            end_date = dt.strptime(start_date, '%Y-%m-%d')
            
        
        all_competitions = wca_function.list_of_events_from(start_date, end_date)
        
        print(len(all_competitions),all_competitions)
        
        q = discord.Embed(title="Iskalec")
        q.add_field(name="Časovno območje",
                    value=f"<t:{int(start_date.timestamp())}:D> - <t:{int(end_date.timestamp())}:D>")
        
        await ctx.send(embed=q)
        
        attending = ""
        
        for comp in all_competitions:
            c = wca_function.competitors_in_comp(comp,nationality.lower())
            if c > 0:
                print(comp)
                
                if c == 1:
                    apnd = f"{c} tekmovalec"
                elif c == 2:
                    apnd = f"{c} tekmovalca"
                elif c in [3,4]:
                    apnd = f"{c} tekmovalci"
                elif c == 5:
                    apnd = f"{c} tekmovalcev"
                
                good,comp_data = wca_function.get_comp_data(comp)
                   
                name = comp_data["name"]
                    
                attending += f"[{name}](https://www.worldcubeassociation.org/competitions/{comp}/registrations)\n* {apnd}\n"
            
        if attending == "":
            attending = "/"
        
        q.add_field(name="Rezultati",value=attending,inline=False)
            
            
        q.add_field(name="Statistika",value=f"Skenirano: {len(all_competitions)} tekmovanj.")
        
        await ctx.send(embed=q)
            
            
            
        
        


def setup(bot: commands.Bot):
    bot.add_cog(userfinderCog(bot))
