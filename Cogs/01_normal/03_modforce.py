import discord
from discord.ext import commands
import requests, json
import functions

from datetime import datetime as dt

import db
from hardstorage import *

mod_roles = db.load_second_table_idd(2) # role
mod_roles = mod_roles["data"]
mod_roles = list(map(int,mod_roles))

with open("settings.json", "r") as config:
    data = json.load(config)
    owner_id = data["owner_id"]

class modforceCog(commands.Cog, name="modforce command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="modforce",
        usage="",
        description="MOD: Delete weekly solves for specific user.",
    )
    @discord.option(name="aa",description="desc",type=discord.Member,required=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def modforce(self, ctx, member: discord.Member):
        
        role_ids = [role.id for role in ctx.author.roles]
        passed = functions.any_object_same(role_ids,mod_roles)
        
        if not passed:
            q = discord.Embed(title="no", description="You don't have permissions to execute this command",color=discord.Colour.blue())
            await ctx.respond(embed=q,ephemeral=True)
            return
    
        userObj = member
        db.create_account(userObj.id)

        user_data = db.get_user_data(userObj.id)
        c_week = functions.this_week()

        f = False
        for i in range(len(user_data["data"]["solves"])):
            if user_data["data"]["solves"][i]["week"] == c_week:
                x = i
                f = True
                break

        if not f:
            week_time = []
        else:
            week_time = user_data["data"]["solves"][x]["data"]

        if week_time == []:
            q = discord.Embed(
                title="Mod hammer has missed its target",
                description="aka. the user you're trying to remove results (weekly) has no weekly results.",
                color=discord.Colour.red(),
            )
            await ctx.respond(embed=q,ephemeral=True)
            return
        
        rem = user_data["data"]["solves"].pop(x)
        
        db.save_user_data(user_data)
        
        q = discord.Embed(title="Mod hammer has hits it's target",description=f"Im looking :eyes: at you {userObj.name}.",color=discord.Colour.green())
        await ctx.send(embed=q)
        
    @discord.command(
        name="deleteall",
        usage="",
        description="SUDO: delete all",
    )
    @discord.option(name="aa",description="desc",type=discord.Member,required=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def deleteall(self, ctx):
        if not ctx.author.id == owner_id:
            q = discord.Embed(title="You shall not use this",description="with great power comes great responsibility")
            await ctx.respond(embed=q)
            return
    
    
        db.delete_database("test")
        q = discord.Embed(title="Deleted all data",description="💀"*5)
        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(modforceCog(bot))
