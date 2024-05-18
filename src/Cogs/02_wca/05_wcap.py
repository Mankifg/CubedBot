import discord
from discord.ext import commands
import requests, json

import src.db as db
from src.hardstorage import * 
import src.wca_functions as wca_functions
import src.functions as functions

USER_ENDPOINT = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{}.json"

def max_len_in_collum(data):
    return [max(len(str(element)) for element in column) for column in zip(*data)]


class wcapCog(commands.Cog, name="wcap command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="wcap", usage="(member:mention) OR (wca id:str)", description="Displays wca profile of user/wca id")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def wcap(self, ctx, member: discord.Member = None, user_wca_id: str = None):

        if user_wca_id is None:
            if member is None:
                userObj = ctx.author
            else:
                userObj = member

            user_data = db.get_user_data(userObj.id)
            wca_id = user_data["wca_id"]

        else:
            wca_id = user_wca_id

        wca_id_exists = wca_functions.wca_id_exists(wca_id)

        if not wca_id_exists:
            q = discord.Embed(
                title=f"Id: **{wca_id}** was not found",
                description="If you think this is an error, please let us know.",
                color=discord.Colour.red(),
            )
            await ctx.send(embed=q)
            return

        user_data = wca_functions.get_wca_data(wca_id)

        picture_url = wca_functions.get_picture_url(wca_id)


        idd = user_data["id"]
        name = user_data["name"]
        country = user_data["country"]
        num_of_comps = user_data["numberOfCompetitions"]
        #medals = user_data["medals"]

        """{
            gold": 0,
            "silver": 0,
            "bronze": 0
        }"""

        q = discord.Embed(
            title=f":flag_{country.lower()}: {name}", description=f"ID: {idd}",
            color=0xFFFFF
        )
        
        q.set_image(url=picture_url)
        #? q.set_author(name="2n2n", icon_url=picture_url) TOO small
        
        '''q.add_field(
            name=f"Medals: {medals['gold']} 🥇{medals['silver']} 🥈{medals['bronze']}🥉",
            value=f"**{num_of_comps}** Competitions", 
            #({num_of_championships} championships)",
            inline=False,
        )'''
        
        q.add_field(name=f"**{num_of_comps}** Competitions",value="_ _")
        
        u_data = {}
        
        for elem in user_data["rank"]["singles"]:
            # elem = {'eventId': event, 'best': int , 'rank': {'world': -1, 'continent': -1, 'country': -1}}
            eventId = elem["eventId"]
            best_time = elem["best"]
            rank = elem["rank"]
            if eventId == "333fm":
                best_time = best_time
            elif eventId == "333mbf":  
                best_time = str(best_time)
                solved = 99 - int(best_time[0:2]) + int(best_time[7:9])
                all_cubes = 99 - int(best_time[0:2]) + 2 * int(best_time[7:9])
                c_time = int(best_time[2:7])
                
                c_time = functions.readify(c_time*100)
                
                best_time = f"{solved}/{all_cubes} {c_time[:-3]}"
                
            else:            
                best_time = functions.readify(best_time)
            
            u_data.update({eventId: {"single": best_time, "singleRank": rank}})
            

        for elem in user_data["rank"]["averages"]:
            # elem = {'eventId': event, 'best': int , 'rank': {'world': -1, 'continent': -1, 'country': -1}}
            eventId = elem["eventId"]
            best_time = elem["best"]
            rank = elem["rank"]
            if eventId == "333fm":
                best_time = int(best_time) / 100
            elif eventId == "333mbf":  
                best_time = str(best_time)
                solved = 99 - int(best_time[0:2]) + int(best_time[7:9])
                all_cubes = 99 - int(best_time[0:2]) + 2 * int(best_time[7:9])
                c_time = int(best_time[2:7])
                
                c_time = functions.readify(c_time*100)
                
                best_time = f"{solved} / {all_cubes} {c_time}"
                
            else:            
                best_time = functions.readify(best_time)
            
            
            u_data.update({eventId: {"single":u_data[eventId]["single"],"singleRank":u_data[eventId]["singleRank"],"avg": best_time, "avgRank": rank}})
            
            
        #print(u_data)
        u_data = functions.sort_weeky_data(u_data)
            
        table = []
        table.append(["Event", "Single", "Average"])
        
        
        for eventId in u_data:
            category_data = u_data[eventId]
            single = category_data["single"]
            event_id_displ = SHORT_DICTIONARY.get(eventId,"/")
            avg = category_data.get("avg","/")
            
            single_line_table = [event_id_displ, single, avg]
            table.append(single_line_table)
            
        #print(table)
        
        max_len = max_len_in_collum(table)
        
        table.insert(1, ["-"*max_len[0],"-"*max_len[1],"-"*max_len[2]])

        new_table = ""
        
        for line in table:
            line = list(map(str,line))
            
            new_table = new_table + f"| {line[0].center(max_len[0])}| {line[1].center(max_len[1])} | {line[2].center(max_len[2])} |\n"
            
        q.add_field(name="PBs", value=f"```\n{new_table}```", inline=False)
        
        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(wcapCog(bot))
