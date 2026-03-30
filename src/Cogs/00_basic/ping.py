import discord
from discord.ext import commands
import time


class PingCog(commands.Cog, name="pping command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="ping",
        usage="",
        description="Display the bot's ping.",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def ping(self, ctx):
        await ctx.respond("Preparing response...", ephemeral=True)
        before = time.monotonic()
        message = await ctx.send("🏓 Pong !")
        ping = (time.monotonic() - before) * 1000
        await message.edit(content=f"🏓 Pong !  `{int(ping)} ms`")


def setup(bot: commands.Bot):
    bot.add_cog(PingCog(bot))
