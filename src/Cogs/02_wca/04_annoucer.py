import discord
from discord.ext import commands
import requests, json

from discord.ext import tasks
import asyncio
from datetime import datetime as dt

import wca_functions
import db
import hardstorage

LAT,LON = 46.0569, 14.5058


class annouceCog(commands.Cog, name="annouce command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.check.start()

    @tasks.loop(seconds=3600)
    async def check(self):
        
        all_comps = []
        c_month = dt.now().month
        c_year = dt.now().year
        print(c_month,c_year)
        
        for i in range(6):
            month = c_month + i
            year = c_year
            if month > 12:
                month = month % 12
                year = year + 1
            
            data = wca_functions.find_by_date(0,month,year)
            
            
            if data is not None:
                all_comps.extend(data)
            
        distanced_comps = wca_functions.filter_by_distance(all_comps)
        
        already_printed_comps = db.load_second_table_idd(3)
        
        channel = db.load_second_table_idd(4)["data"]["send_channel"]
        channel = int(channel)
        ch = self.bot.get_channel(channel)
        
        final_comps = []
        
        for comp in distanced_comps:
            comp_id = comp["id"]
            
            if not comp_id in already_printed_comps["data"]["comps"]:
                final_comps.append(comp)
                
        
        send = []
        for comp in final_comps:
            
            comp_id = comp["id"]
            success, data = wca_functions.get_comp_data(comp_id)
            
            if not success:
                continue
            else:
                q = discord.Embed(
                    title=f":flag_{data['country'].lower()}: | {data['name']}",
                    description=f"{data['city']}, {wca_functions.COUNTRIES_DICT.get(data['country'])} | [{data['id']}](https://www.worldcubeassociation.org/competitions/{data['id']})",
                    color=discord.Colour.blue(),
                )
                start_date = data["date"]["from"]
                end_date = data["date"]["till"]
                
                if start_date == end_date:
                    date = f'<t:{int(dt.strptime(start_date, "%Y-%m-%d").timestamp())}:D>'
                else:
                    start_date = dt.strptime(start_date, "%Y-%m-%d").timestamp()
                    end_date = dt.strptime(end_date, "%Y-%m-%d").timestamp()
                    date = f"<t:{int(start_date)}:D> - <t:{int(end_date)}:D> ({data['date']['numberOfDays']})"
                    
                q.add_field(name="Datum", value=date, inline=False)
                
                #*********
                events = data["events"]
                
                for i in range(len(events)):
                    events[i] = hardstorage.SHORT_DICTIONARY.get(events[i])
                
                q.add_field(name="Discipline", value=", ".join(events), inline=False)

                #?*********
                organizator = "\n".join([f"{org['name']}" for org in data["organisers"]])
                q.add_field(name="Organizator(ji)", value=organizator, inline=True,)

                #*********
                delegates = "\n".join([ f"{delegate['name']}" for delegate in data["wcaDelegates"]])
                q.add_field(name="WCA Delegati", value=delegates, inline=True)
                
                #*********
                q.add_field(name="Prizorišče", value=f"{data['venue']['name']}\n{data['venue']['address']}\n{data['venue']['details']}", inline=False,)

                if data["externalWebsite"]:
                    q.add_field(name="Spletna stran", value=data["externalWebsite"], inline=False)

            send_msg = await ch.send(embed=q)
            print("send",comp_id)
            
            await send_msg.add_reaction("🟢")
            await send_msg.add_reaction("🟡")
            await send_msg.add_reaction("🔴")
            
            send.append(comp_id)
            
            await asyncio.sleep(5)
            
        
        
        for comp_id in send:
            if not comp_id in already_printed_comps["data"]["comps"]:
                already_printed_comps["data"]["comps"].append(comp_id)
                
        
        db.save_second_table_idd(already_printed_comps)
    
    @check.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()
        

def setup(bot: commands.Bot):
    bot.add_cog(annouceCog(bot))
