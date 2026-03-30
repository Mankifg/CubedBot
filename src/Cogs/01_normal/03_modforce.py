import discord
from discord.ext import commands
import requests, json
import src.functions as functions

from datetime import datetime as dt

import src.db as db
from src.hardstorage import *
from src.guild_access import ensure_primary_guild, primary_guild_ids

mod_roles = db.load_second_table_idd(2) # role
mod_roles = mod_roles["data"]
mod_roles = list(map(int,mod_roles))


class modforceCog(commands.Cog, name="modforce command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="modforce",
        usage="(member:mention)",
        description="MOD: Delete weekly solves for specific user.",
        guild_ids=primary_guild_ids(),
    )
    @discord.option(name="aa",description="User whose weekly solves should be removed.",type=discord.Member,required=True)
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def modforce(self, ctx, member: discord.Member):
        if not await ensure_primary_guild(ctx, self.bot):
            return
        await ctx.respond("Preparing response...", ephemeral=True)
        
        role_ids = [role.id for role in ctx.author.roles]
        passed = functions.any_object_same(role_ids,mod_roles)
        
        if not passed:
            q = discord.Embed(title="no", description="You don't have permissions to execute this command",color=discord.Colour.blue())
            await ctx.send(embed=q,ephemeral=True)
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
            await ctx.send(embed=q,ephemeral=True)
            return
        
        rem = user_data["data"]["solves"].pop(x)
        
        db.save_user_data(user_data)
        
        q = discord.Embed(title="Mod hammer has hits it's target",description=f"Im looking :eyes: at you {userObj.name}.",color=discord.Colour.green())
        await ctx.send(embed=q)

def setup(bot: commands.Bot):
    bot.add_cog(modforceCog(bot))
