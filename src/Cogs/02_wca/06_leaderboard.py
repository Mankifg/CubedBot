import discord
from discord.ext import commands
import requests, json

import src.db as db
from src.hardstorage import * 

import src.wca_function as wca_function


def max_len_in_collum(data):
    return [max(len(str(element)) for element in column) for column in zip(*data)]


class leaderboardCog(commands.Cog, name="leaderboard command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="leaderboard", usage="(member:mention) OR (wca id:str)", description="Displays wca profile of user/wca id")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def leaderboard(self, ctx, options1):

        print(1)


def setup(bot: commands.Bot):
    bot.add_cog(leaderboardCog(bot))
