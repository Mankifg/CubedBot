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

COMP_URL = "https://www.worldcubeassociation.org/competitions/{}"
REGISTERED_URL = "https://www.worldcubeassociation.org/api/v1/competitions/{}/registrations"
NUMBER_OF_DAYS_TO_SEARCH = 7
CHANNEL_ANNOUCE = "957586553536921620"
URL_FOR_REGIONS = "https://www.worldcubeassociation.org/api/v0/countries"

raw_regions = requests.get(URL_FOR_REGIONS).json()
if isinstance(raw_regions, dict):
    raw_regions = raw_regions.get("items", [])
if not isinstance(raw_regions, list):
    raw_regions = []

REGIONS = []
ISO2 = []
for elem in raw_regions:
    if not isinstance(elem, dict):
        continue
    iso2 = elem.get("iso2Code") or elem.get("iso2")
    name = elem.get("name")
    if not isinstance(iso2, str) or not isinstance(name, str):
        continue
    ISO2.append(iso2.lower())
    REGIONS.append(f"{iso2.lower()} - {name}")

print(ISO2)

def convert_to_abbreviated_form(full_name):
    print(full_name)
    name_parts = full_name.strip().split()
    if len(name_parts) < 2:
        raise ValueError("Full name must include at least a first name and a surname.")
    first_names_and_middle = name_parts[:-1]
    last_surname = name_parts[-1]
    abbreviated_names = [name[0].upper() + '.' for name in first_names_and_middle]
    return " ".join(abbreviated_names + [last_surname.capitalize()])


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
        '''
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
    '''
    async def get_regions(ctx: discord.AutocompleteContext):
        return REGIONS        
    
    @discord.command(name="userfinder", usage="(nationality) [start date: YYYY-MM-DD] [end date: YYYY-MM-DD]", description="Given nationality and time frame finds competitors who are competing")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def userFinder(
        self, ctx: discord.ApplicationContext,
        nationality: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_regions)), # type: ignore
        #   test: discord.Option(Attachment), # type: ignore
        user_start_date:str=None,
        end_date:str=None,
        ):
        
        nat = nationality.split("-")[0].strip()
        if nat not in ISO2:
            print(nat)
            error = discord.Embed(title="Region should be picked from one of the provided ones",
                                  description="Izbrati je potrebo eno izmed regij iz seznama.",
                                  color=discord.Colour.red())
            await ctx.respond(embed=error)
            return
        await ctx.respond("Preparing response...", ephemeral=True)
        
        start_date = dt.now()
        if valid_time(user_start_date):
            start_date = dt.strptime(user_start_date, '%Y-%m-%d')
            
        if end_date is None:
            end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)  
        elif end_date.isnumeric():
            end_date = start_date + timedelta(days=int(end_date))
        elif not valid_time(end_date):
            end_date = start_date + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)
        else:
            end_date = dt.strptime(end_date, '%Y-%m-%d')
            
        all_competitions = wca_function.list_of_events_from(start_date, end_date)
        
        print(len(all_competitions),all_competitions)
        
        q = discord.Embed(title=f"Iskalec tekmovanj")
        q.add_field(name="Obdobje",
                    value=f"<t:{int(start_date.timestamp())}:D> - <t:{int(end_date.timestamp())}:D>")
        
        first_send = await ctx.send(embed=q)

        s_time = time.time()
        
        atLeastOneComp = False
        fetch_failures = 0
        
        
        send_obj = []
        send_single = ""
        
        for competition_id in all_competitions:
            print("trying:",competition_id,end=" ")

            resp = None
            for _ in range(4):
                try:
                    resp = await asyncio.to_thread(
                        requests.get,
                        REGISTERED_URL.format(competition_id),
                        timeout=4,
                    )
                    print("trying ",resp.status_code)
                    if resp.status_code == 200:
                        break
                except requests.RequestException:
                    print("req timeout",competition_id)
                    resp = None
                
            if resp is None or resp.status_code != 200:
                fetch_failures += 1
                continue

            print(resp.status_code)
            try:
                resp = resp.json()
            except ValueError:
                fetch_failures += 1
                continue
            
            matching_competitors = 0
            
            for user in resp:
                # {'user': 
                # {'id': XXX, 'name': 'XXX', 'wca_id': 'XXXXXXXXX', 'gender': 'X', 'country_iso2': 'XX', 
                # 'country': {'id': 'XXXXXXXX', 'name': 'XXXXXX', 'continentId': '_XXXXXXX', 'iso2': 'XX'}, 'class': 'user'}, 
                # 'user_id': XXX, 'competing': {'event_ids': ['XXX', 'XXX', 'XXX']}}
                iso2_code = user["user"]["country_iso2"]
                
                if iso2_code.lower() == nat.lower():
                    matching_competitors += 1
                    
                  
            if matching_competitors > 0:
                atLeastOneComp = True
                success, comp_data = await asyncio.to_thread(wca_function.get_comp_data, competition_id)
                competition_name = competition_id
                if success:
                    competition_name = comp_data.get("name", competition_id)

                if matching_competitors == 1:
                    plural = "tekmovalec"
                elif matching_competitors == 2:
                    plural = "tekmovalca"
                elif matching_competitors in [3, 4]:
                    plural = "tekmovalci"
                else:
                    plural = "tekmovalcev"

                to_add:str = f"* [{competition_name}]({COMP_URL.format(competition_id)})\n  • {matching_competitors} {plural}\n"
                if (len(send_single) +len(to_add) > 1024):
                    send_obj.append(send_single)
                    send_single = to_add
                else:
                    send_single += to_add
                    
        if (send_single != ""):
            send_obj.append(send_single)

        if not atLeastOneComp:
            send_obj = ["Ni rezultatov."]
        
        e_time = time.time()

        
        q.add_field(name=f"Tekmovanja, kjer so prijavljeni tekmovalci regije: {nationality.title()}",value=send_obj[0],inline=False)
        
        q.add_field(
            name="Statistika",
            value=f"Skenirano: {len(all_competitions)} tekmovanj. Čas: {int(round(e_time-s_time))} sec"
        )
        print("ready to send")
        await first_send.edit(embed=q)
        print("send")
        
        if (len(send_obj) > 1):
            for i in range(1,len(send_obj)):
                send_single = send_obj[i]
                
                q = discord.Embed(title=f"{i+1}. del")
                q.add_field(name=".",value=send_single)
                await ctx.send(embed=q)

            
    
def setup(bot: commands.Bot):
    bot.add_cog(userfinderCog(bot))
