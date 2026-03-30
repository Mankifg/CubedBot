import discord
from discord.ext import commands
import time
import subprocess


def _current_version():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except Exception:
        return "unknown"


class PingCog(commands.Cog, name="pping command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.version = _current_version()

    @discord.command(
        name="ping",
        usage="",
        description="Display the bot's ping.",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def ping(self, ctx):
        await ctx.respond("Preparing response...", ephemeral=True)
        before = time.monotonic()
        message = await ctx.send(f"🏓 Pong !\n⚙️ Build: `{self.version}`")
        ping = (time.monotonic() - before) * 1000
        await message.edit(content=f"🏓 Pong !  `{int(ping)} ms`\n⚙️ Build: `{self.version}`")


def setup(bot: commands.Bot):
    bot.add_cog(PingCog(bot))
