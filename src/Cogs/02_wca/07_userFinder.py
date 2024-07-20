import discord
from discord.ext import commands, tasks
import requests, json

from datetime import datetime as dt
import datetime
from datetime import timedelta
import time
import asyncio

import src.db as db
from src.hardstorage import * 

import src.wca_function as wca_function

COMP_ULR = "https://www.worldcubeassociation.org/competitions/{}/registrations"
NUMBER_OF_DAYS_TO_SEARCH = 7
CHANNEL_ANNOUCE = "957586553536921620"


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
        self.userf.start()
        
        
    @tasks.loop(seconds=58*60)
    async def userf(self):
        if dt.now().weekday == 2 and dt.now().hour == 8: 
            print("Sending")
            
            start_date = dt.now()        
            end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)  
            all_competitions = wca_function.list_of_events_from(start_date, end_date)
            
            print(len(all_competitions),all_competitions)
            
            q = discord.Embed(title=f"Iskalec tekmovanj")
            q.add_field(name="Časovno območje",
                        value=f"<t:{int(start_date.timestamp())}:D> - <t:{int(end_date.timestamp())}:D>")
            
            
            ch = self.bot.get_channel(957586553536921620)
            
            first_send = await ch.send(embed=q)
            attending = ""
            
            s_time = time.time()
            for comp in all_competitions:
                c = wca_function.competitors_in_comp(comp,"slovenia".lower())
                if c > 0:
                    print(comp)
                    
                    if c == 1:
                        apnd = f"{c} tekmovalec"
                    elif c == 2:
                        apnd = f"{c} tekmovalca"
                    elif c in [3,4]:
                        apnd = f"{c} tekmovalci"
                    else:
                        apnd = f"{c} tekmovalcev"
                    
                    good,comp_data = wca_function.get_comp_data(comp)
                    
                    name = comp_data["name"]
                        
                    attending += f"[{name}](https://www.worldcubeassociation.org/competitions/{comp}/registrations)\n* {apnd}\n"
            e_time = time.time()
            if attending == "":
                attending = "/"
            
            q.add_field(name=f"Tekmovanja v izbranem obdobju, kjer so prijavljeni tekmovalci regije: {'slovenia'.title()}",value=attending,inline=False)
            q.add_field(name="Statistika",value=f"Skenirano: {len(all_competitions)} tekmovanj. Čas: {int(e_time-s_time)} sec")
            
            await first_send.edit(embed=q)
            
            await asyncio.sleep(10*60)

                
                
    @userf.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()

   
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
        
        q = discord.Embed(title=f"Iskalec tekmovanj")
        q.add_field(name="Časovno območje",
                    value=f"<t:{int(start_date.timestamp())}:D> - <t:{int(end_date.timestamp())}:D>")
        
        first_send = await ctx.send(embed=q)
        attending = ""
        
        s_time = time.time()
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
                else:
                    apnd = f"{c} tekmovalcev"
                
                good,comp_data = wca_function.get_comp_data(comp)
                   
                name = comp_data["name"]
                    
                attending += f"[{name}](https://www.worldcubeassociation.org/competitions/{comp}/registrations)\n* {apnd}\n"
        e_time = time.time()
        if attending == "":
            attending = "/"
        
        q.add_field(name=f"Tekmovanja v izbranem obdobju, kjer so prijavljeni tekmovalci regije: {nationality.title()}",value=attending,inline=False)
        q.add_field(name="Statistika",value=f"Skenirano: {len(all_competitions)} tekmovanj. Čas: {int(e_time-s_time)} sec")
        
        await first_send.edit(embed=q)
            
    
def setup(bot: commands.Bot):
    bot.add_cog(userfinderCog(bot))
