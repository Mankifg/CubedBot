import discord
from discord.ext import commands
import requests, json

import src.db as db
from src.hardstorage import * 
from src.guild_access import ensure_primary_guild

import src.wca_function as wca_function


def max_len_in_collum(data):
    return [max(len(str(element)) for element in column) for column in zip(*data)]


class leaderboardCog(commands.Cog, name="leaderboard command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="leaderboard", usage="wip", description="wip")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def leaderboard(self, ctx, options1):
        if not await ensure_primary_guild(ctx, self.bot):
            return

        print(1)


def setup(bot: commands.Bot):
    bot.add_cog(leaderboardCog(bot))
