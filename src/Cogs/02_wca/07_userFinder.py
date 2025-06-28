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
URL_FOR_REGIONS = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/countries.json"

data = requests.get(URL_FOR_REGIONS).json()["items"]
REGIONS = []
ISO2 = []
for elem in data:
    ISO2.append(elem['iso2Code'].lower())
    REGIONS.append(f"{elem['iso2Code'].lower()} - {elem['name']}")

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
        start_date:str=None,
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
            end_date = dt.strptime(end_date, '%Y-%m-%d')
            
        all_competitions = wca_function.list_of_events_from(start_date, end_date)
        
        print(len(all_competitions),all_competitions)
        
        q = discord.Embed(title=f"Iskalec tekmovanj")
        q.add_field(name="Obdobje",
                    value=f"<t:{int(start_date.timestamp())}:D> - <t:{int(end_date.timestamp())}:D>")
        
        first_send = await ctx.send(embed=q)

        s_time = time.time()
        
        atLeastOneComp = False
        responding = ""
        for competition_id in all_competitions:
            print("trying:",competition_id,end=" ")
            try:
                resp = requests.get(REGISTERED_URL.format(competition_id))
                print(resp.status_code)
                resp = resp.json() 
                
                goingNum = 0
                
                for user in resp:
                    # {'user': 
                    # {'id': XXX, 'name': 'XXX', 'wca_id': 'XXXXXXXXX', 'gender': 'X', 'country_iso2': 'XX', 
                    # 'country': {'id': 'XXXXXXXX', 'name': 'XXXXXX', 'continentId': '_XXXXXXX', 'iso2': 'XX'}, 'class': 'user'}, 
                    # 'user_id': XXX, 'competing': {'event_ids': ['XXX', 'XXX', 'XXX']}}
                    iso2_code = user["user"]["country_iso2"]
                    
                    if iso2_code.lower() == nat.lower():
                        goingNum += 1
                        
                        
                if goingNum > 0:
                    atLeastOneComp = True
                    
                    comp_data = requests.get(f"https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/competitions/{competition_id}.json").json()
                    
                    
                    responding += f"[{comp_data['name']}]({COMP_URL.format(competition_id)})\n"#\n* {goingNames}"
            except Exception as e:
                print("nea gre")
                print(e)       
            

        if not atLeastOneComp:
            responding = "Ni rezultatov."
        
        e_time = time.time()

        q.add_field(name=f"Tekmovanja, kjer so prijavljeni tekmovalci regije: {nationality.title()}",value=responding,inline=False)
        q.add_field(name="Statistika",value=f"Skenirano: {len(all_competitions)} tekmovanj. Čas: {int(round(e_time-s_time))} sec")
        print("ready to send")
        await first_send.edit(embed=q)
        print("send")
        print("backup")
        await ctx.send(embed=q)
        print("final final")
            
    
def setup(bot: commands.Bot):
    bot.add_cog(userfinderCog(bot))
