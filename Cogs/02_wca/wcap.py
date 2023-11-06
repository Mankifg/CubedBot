import discord
from discord.ext import commands
import requests, json

import db


class wcapCog(commands.Cog, name="wcap command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="wcap", usage="", description="")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def wcap(self, ctx):
        id = ctx.author.id

        await ctx.respond()


def setup(bot: commands.Bot):
    bot.add_cog(wcapCog(bot))
