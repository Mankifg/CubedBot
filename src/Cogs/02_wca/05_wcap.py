import discord
from discord.ext import commands
import requests, json

import src.db as db
from src.hardstorage import * 
import src.wca_function as wca_function
import src.functions as functions

def max_len_in_collum(data):
    return [max(len(str(element)) for element in column) for column in zip(*data)]

ARRY_FOR_WCA_ID_SORT = ["333","222","444","555","666","777","333bf","333fm","333oh","clock","minx","pyram","skewb","sq1","444bf","555bf","333mbf",]
BLIND_LABELS = {
    "333bf": "3BLD",
    "444bf": "4BLD",
    "555bf": "5BLD",
    "333mbf": "MBLD",
}

def custom_sort_key(key):
    try:
        return ARRY_FOR_WCA_ID_SORT.index(key)
    except ValueError:
        return float('inf')



class wcapCog(commands.Cog, name="wcap command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="wcap", usage="(member:mention) OR (wca id:str)", description="Displays wca profile of user/wca id")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def wcap(self, ctx, member: discord.Member = None, user_wca_id: str = None):
        await ctx.respond("Preparing response...", ephemeral=True)

        if user_wca_id is None:
            if member is None:
                userObj = ctx.author
            else:
                userObj = member

            user_data = db.get_user_data(userObj.id)
            wca_id = user_data["wca_id"]

        else:
            wca_id = user_wca_id

        if not wca_id:
            q = discord.Embed(
                title="No WCA ID linked",
                description="Use `/changewcaid <WCA_ID>` first, or provide `user_wca_id` in this command.",
                color=discord.Colour.orange(),
            )
            await ctx.send(embed=q, ephemeral=True)
            return

        wca_id_exists = wca_function.wca_id_exists(wca_id)

        if not wca_id_exists:
            q = discord.Embed(
                title=f"Id: **{wca_id}** was not found",
                description="If you think this is an error, please let us know.",
                color=discord.Colour.red(),
            )
            await ctx.send(embed=q)
            return

        user_data = wca_function.get_wca_data(wca_id)
        if not user_data:
            q = discord.Embed(
                title="WCA profile unavailable",
                description="Could not load this profile right now. Please try again in a moment.",
                color=discord.Colour.red(),
            )
            await ctx.send(embed=q)
            return

        picture_url = wca_function.get_picture_url(wca_id)


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
        
        if picture_url:
            q.set_thumbnail(url=picture_url)
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
                
            print(best_time,"with info ",eventId)  
            
            best_time = functions.convert_to_human_frm(best_time,eventId)
            
            u_data.update({eventId: {"single": best_time, "singleRank": rank}})
        
        print("aaa")            

        for elem in user_data["rank"]["averages"]:
            # elem = {'eventId': event, 'best': int , 'rank': {'world': -1, 'continent': -1, 'country': -1}}
            eventId = elem["eventId"]
            best_time = elem["best"]
            rank = elem["rank"]
            
            print(best_time,"with info ",eventId)  
            best_time = functions.convert_to_human_frm(best_time)
            print(best_time)
            
            u_data[eventId].update({"avg": best_time, "avgRank": rank})
            
            
        #print(u_data)
        u_data = functions.sort_weeky_data(u_data)
            
        table = []
        print(u_data.keys())
        u_data = dict(sorted(u_data.items(), key=lambda item: custom_sort_key(item[0])))
        print(u_data.keys())
        table.append(["Event", "Single", "Average"])

        for eventId in u_data:
            category_data = u_data[eventId]
            single = str(category_data["single"]).replace("\n", " ").replace("\r", " ").strip()
            avg = str(category_data.get("avg","/")).replace("\n", " ").replace("\r", " ").strip()
            event_id_displ = BLIND_LABELS.get(eventId, SHORT_DICTIONARY.get(eventId, "/"))
            single_line_table = [event_id_displ, single, avg]
            table.append(single_line_table)

        max_len = max_len_in_collum(table)
        table.insert(1, ["-"*max_len[0],"-"*max_len[1],"-"*max_len[2]])

        new_table = ""
        for line in table:
            line = list(map(str, line))
            new_table = new_table + f"| {line[0].center(max_len[0])}| {line[1].center(max_len[1])} | {line[2].center(max_len[2])} |\n"

        q.add_field(name="PRs", value=f"```\n{new_table}```", inline=False)
        
        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(wcapCog(bot))
