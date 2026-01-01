import discord
from discord.ext import commands
import requests, json

from datetime import datetime as dt

import src.functions as functions
import src.db as db
import src.hardstorage as hs


mod_roles = db.load_second_table_idd(2) # role
mod_roles = mod_roles["data"]
mod_roles = list(map(int,mod_roles))

def real_week():
    now = dt.now()
    return f"{now.year}-{now.isocalendar()[1]}"

class newweekCog(commands.Cog, name="newweek command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="newweek",
        usage="(week:str)",
        description="MOD: Changes to next week, because we can't trust calendar.",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def newweek(self, ctx, week:str="",discipline:str=""):
        
        role_ids = [role.id for role in ctx.author.roles]
        passed = functions.any_object_same(role_ids,mod_roles)
        
        if not passed:
            q = discord.Embed(title="no", description="You don't have permissions to execute this command",color=discord.Colour.blue())
            await ctx.respond(embed=q,ephemeral=True)
            return
        
        database_week_entrys = db.load_second_table_idd(1)  # week
        
        all_week_data:list[str] = database_week_entrys["data"]["old"]
        next_week:dict[str,list[str]] = database_week_entrys["data"]["current"]
        '''
        {
            "name":"-1",
            "events": ["333","222","sq1",...],
        }
        
        '''
        
        if week == "":
            q = discord.Embed(title="Looks like you didn't supliled week name",color=discord.Color.orange())
            q.set_footer(text=f"Just to lyk calander week is {real_week()}, but it may or may not be in db.") # leet you know
            
            await ctx.send(embed=q)
            return
        
        if week in all_week_data:
            q = discord.Embed(title="This week name is already in database",description="And you don't want to change that")
            q.add_field(name="Please use new name.",value="thanks")
            
            q.set_footer(text=f"Just to lyk calander week is {real_week()}, but it may or may not be in db.") # leet you know
            await ctx.send(embed=q)
            return
        
       
        all_possible_event = hs.CATEGORIES_SORTED
        discipline_list = discipline.split(",")
        
        for dis in discipline_list:
            if (dis not in all_possible_event):
                q = discord.Embed(title="Aborting",description=f"Event with id: {dis} not found in database")
                q.add_field(name="Events:",value="333,222,444,555,333oh,pyram,skewb,clock,minx,sq1,666,777,333bf,444bf,555bf")
                q.set_footer(text="If you think this is an error contact bot admin.")
                await ctx.send(embed=q)
                return
            

       
        database_week_entrys["data"]["current"]["name"] = week
        database_week_entrys["data"]["current"]["events"] = discipline_list
        database_week_entrys["data"]["old"].append(week)
        
        
        precisceno_bes = f"* {'[NL]* '.join(discipline_list)}"
        precisceno_bes = precisceno_bes.replace("[NL]","\n")
        
        q = discord.Embed(title=f"Novi teden: **{week}**",color=discord.Color.blue())
        q.add_field(name="Discipline",value=precisceno_bes)
        
        db.save_second_table_idd(database_week_entrys)
        
        await ctx.send(embed=q)
        
        
        
        
       

            


def setup(bot: commands.Bot):
    bot.add_cog(newweekCog(bot))
