import discord
from discord.ext import commands
import requests, json
import re

cube_notation_pattern = re.compile(r'^([FBRLUDMESxyzwfbrludmesxyz2\']+ ?)+$')

# Example usage:


WCA_COMP_INCLUDE = "worldcubeassociation.org/competitions"

class messagesCog(commands.Cog, name="messages command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        
        if msg.author == self.bot.user:
            return
        
        message = msg.content
        
        
        print(message)
        
        matches = cube_notation_pattern.findall(message)
        if matches:
            await msg.add_reaction("🧊")

            #await msg.channel.send(f"{matches}")
    


def setup(bot: commands.Bot):
    bot.add_cog(messagesCog(bot))
