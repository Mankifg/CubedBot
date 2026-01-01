import discord
from discord.ext import commands
import requests, json

from datetime import datetime as dt

import src.functions as functions
import src.db as db


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
    async def newweek(self, ctx, week:str=""):
        
        role_ids = [role.id for role in ctx.author.roles]
        passed = functions.any_object_same(role_ids,mod_roles)
        
        if not passed:
            q = discord.Embed(title="no", description="You don't have permissions to execute this command",color=discord.Colour.blue())
            await ctx.respond(embed=q,ephemeral=True)
            return
        
        cw = db.load_second_table_idd(1)  # week
        
        all_week_data = cw["data"]["old"]
        current_week = cw["data"]["data"]
        
        if week == None:
            q = discord.Embed(title="Looks like you didn't supliled week name",color=discord.Color.orange())
            q.set_footer(text=f"Just to lyk calander week is {real_week()}, but it may or may not be in db.") # leet you know
            
            await ctx.send(embed=q)
            return
        
        if week in all_week_data and not week is None:
            q = discord.Embed(title="This week name is already in database",description="And you don't want to change that")
            q.add_field(name="Please use new name.",value="thanks")
            
            q.set_footer(text=f"Just to lyk calander week is {real_week()}, but it may or may not be in db.") # leet you know
            await ctx.send(embed=q)
            return
        
        if not week in all_week_data: 
            current_week = week
            q = discord.Embed(title=f"Changed week name. -> {current_week}",color=0xFFFFF)
            cw["data"]["data"] = current_week
            cw["data"]["old"].append(current_week)
            db.save_second_table_idd(cw)
            
            await ctx.send(embed=q)
            return 
        
        
        
       

            


def setup(bot: commands.Bot):
    bot.add_cog(newweekCog(bot))
