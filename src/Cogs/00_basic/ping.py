import discord
from discord.ext import commands
import time
import subprocess
from src.guild_access import both_guild_ids


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
        guild_ids=both_guild_ids(),
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def ping(self, ctx):
        await ctx.defer()
        ping = self.bot.latency * 1000
        await ctx.respond(f"🏓 Pong !  `{int(ping)} ms`\n⚙️ Build: `{self.version}`")


def setup(bot: commands.Bot):
    bot.add_cog(PingCog(bot))
