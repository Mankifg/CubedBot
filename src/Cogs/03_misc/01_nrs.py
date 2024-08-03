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

class nrCog(commands.Cog, name="nr command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.wca_live_check.start()


    @discord.command(name="nr", usage="", description="")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def nr(self, ctx,):
        pass

    @tasks.loop(seconds=900)
    async def wca_live_check(self):

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
        
        for record in resp:
            if record["result"]["person"]["country"]["iso2"] == "SI":
                passing.append(record)
                
        already_submited = db.load_second_table_idd("5")
        
        print(already_submited)   
                    
        for record in passing:
            if not record["id"] in already_submited["data"]["already_sent"]:
                print("RECORD FOUND !!!", record)
                
                titl = f'{record["tag"]} | {record["type"]}'
                
                if record["tag"] == "NR":
                    q = discord.Embed(title=titl,color=discord.Colour.green())
                elif record["tag"] == "CR":
                    q = discord.Embed(title=titl,color=discord.Colour.yellow())
                else:
                    q = discord.Embed(title=titl,color=discord.Colour.red())
                    
                
                person = record["result"]["person"]
                round_obj = record["result"]["round"]
                
                q.add_field(
                    name=f':flag_{person["country"]["iso2"].lower()}: | {person["name"]}', # ( https://www.worldcubeassociation.org/persons/{person["wcaId"]} )',
                    value=f'{person["wcaId"]}', 
                )
                
                q.add_field(
                    name=f'{round_obj["competitionEvent"]["event"]["name"]}',
                    value=f'{round_obj["competitionEvent"]["competition"]["name"]}',
                    inline=False,
                )
                
                times = []
                for el in record["result"]["attempts"]:
                    times.append(el["result"])
                    
                if record["type"] == "average":  
                                 
                    q.add_field(
                        name=f'SOLVES:',
                        value=f'```{functions.beutify(times,round_obj["competitionEvent"]["event"]["id"])}```',
                    )
                else:
                    times = [x for x in times if x != -1]

                    q.add_field(
                        name=f'SINGLE: ```{functions.readify(min(times))}```',
                        value=f'SOLVES: {functions.beutify(times,round_obj["competitionEvent"]["event"]["id"])}',
                    )
                
                if record["tag"] == "NR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/nr.png")
                elif record["tag"] == "CR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/cr.png")
                elif record["tag"] == "WR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/wr.png")
                else:
                    print("[ERROR] not nr,cr or wr?")
                
                channel = int(already_submited["data"]["channel"])
                ch = self.bot.get_channel(channel)
                
                await ch.send(embed=q)
                print("send")
                
                already_submited["data"]["already_sent"].append(record["id"])
                db.save_second_table_idd(already_submited)
                
                
    @wca_live_check.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
