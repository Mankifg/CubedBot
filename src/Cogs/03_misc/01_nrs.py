import discord
from discord.ext import commands
import requests, json

from discord.ext import tasks
import asyncio
from datetime import datetime as dt

import src.wca_function as wca_function
import src.db as db
import src.hardstorage as hardstorage
import src.functions as functions

FILE_PATH = "settings.json"

def get_channel(channel_type):
    with open(FILE_PATH) as f:
        data = json.load(f)

    if channel_type == "nr":
        return data["records"]["channel"]
    else:   
        return -1        

def already_sent_nr(nr):
    """
    if nr already sent:
        1 - already sent nr
        
        0 - first time seeing nr && will update
        
    """
    print("chekcing nr",nr)
    with open(FILE_PATH,"r") as f:
        data = json.load(f)
        print(data)
    print(nr in data["records"]["sent"])
    if not (nr in data["records"]["sent"]):
        print("ins")
        data["records"]["sent"].append(nr)
        with open(FILE_PATH,"w") as f:
            json.dump(data,f)
        print("dmps")
        print(0)
        return 0
    print(1)
    return 1

class nrCog(commands.Cog, name="nr command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.wca_live_check.start()


    @tasks.loop(seconds=900)
    async def wca_live_check(self):
        print("[INFO] wca live record check")
        resp = requests.post(
            url="https://live.worldcubeassociation.org/api/graphql",
            json={
                "query": """
                query {
                    recentRecords {
                    id
                    type
                    tag
                    attemptResult
                    result {
                        attempts {
                        result
                        }
                        person {
                        name
                        wcaId
                        country {
                            iso2
                            name
                        }
                        }
                        round {
                        id
                        competitionEvent {
                            event {
                            id
                            name
                            }
                            competition {
                            id
                            name
                            }
                        }
                        }
                    }
                    }
                }
                """
            },
        ).json()["data"]["recentRecords"]
        
      
        passing = []
        print(len(resp))
        for record in resp:
            if record["result"]["person"]["country"]["iso2"] == "SI":
                passing.append(record)
        print(len(passing))
            
        for record in passing:
            print(record["id"])
            #print("fdfff",already_sent_nr(record["id"]))
            if not already_sent_nr(record["id"]):
                print("RECORD FOUND !!!", record)
                
                titl = f'{record["tag"]} {record["type"]}'
                
                if record["tag"] == "NR":
                    q = discord.Embed(title=titl,color=discord.Colour.green())
                elif record["tag"] == "CR":
                    q = discord.Embed(title=titl,color=discord.Colour.yellow())
                else:
                    q = discord.Embed(title=titl,color=discord.Colour.red())
                    
                
                person = record["result"]["person"]
                round_obj = record["result"]["round"]
                
                q.add_field(
                    name=f':flag_{person["country"]["iso2"].lower()}: {person["name"]}', # ( https://www.worldcubeassociation.org/persons/{person["wcaId"]} )',
                    value=f'[{person["wcaId"]}](https://www.worldcubeassociation.org/persons/{person["wcaId"]})', 
                )
                
                q.add_field(
                    name=f'{round_obj["competitionEvent"]["event"]["name"]}',
                    value=f'{round_obj["competitionEvent"]["competition"]["name"]}',
                    inline=False,
                )
                
                times = []
                for el in record["result"]["attempts"]:
                    times.append(el["result"])
                    
                event_id = round_obj["competitionEvent"]["event"]["id"]
                    
                    
                top_title = ""
                if record["type"] == "average":
                    top_title += "AVERAGE:"
                else:
                    top_title += "SINGLE:"

                top_title += f' ```{functions.convert_to_human_frm(record["attemptResult"],event_id)}```'
                bottom_title = f'SOLVES: `{functions.arry_to_human_frm(times,event_id)}`'
                
                q.add_field(name=top_title,value=bottom_title)               
                    
                """if record["type"] == "average":  
                                 
                    q.add_field(
                        name=f'AVERAGE: ```{functions.convert_to_human_frm(functions.avg_of(times,event_id))}```',
                        value=f'SOLVES: `{functions.arry_to_human_frm(times,event_id)}`',
                    )
                else:
                    q.add_field(
                        name=f'SINGLE: ```{functions.convert_to_human_frm(record["attemptResult"],event_id)}```',
                        value=f'SOLVES: `{functions.arry_to_human_frm(times,event_id)}`',
                    )
                """
                
                if record["tag"] == "NR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/nr.png")
                elif record["tag"] == "CR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/cr.png")
                elif record["tag"] == "WR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/wr.png")
                else:
                    print("[ERROR] not nr,cr or wr?")
                
        
                
                channel = get_channel("nr")
                ch = self.bot.get_channel(channel)
                
                await ch.send(embed=q)
                print("sent")
                
              
                
                
    @wca_live_check.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
