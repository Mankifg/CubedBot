from pathlib import Path
from itertools import cycle
import os
from dotenv import load_dotenv
import time
import subprocess
import discord
from discord.ext import tasks, commands

start_time = time.time()

load_dotenv()
token = os.getenv("TOKEN")

import src.db as db

status = cycle(
    [
        "Made by Mankifg",
        "Some commands are used, because we can't trust the calendar.",
    ]
)

@tasks.loop(seconds=30)
async def status_swap():
    await bot.change_presence(activity=discord.Game(next(status)))


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("m!"),
    help_command=None,
    description="Mankifg's discord bot.",
    intents=intents,
    owner_id=650756055390879757,
)
bot.startup_ping_sent = False

setup_time = time.time()

if __name__ == "__main__":
    for path in Path("./src/Cogs").rglob("*.py"):

        p = str(path)
        p = p.replace("\\", ".")
        p = p.replace("/", ".")
        print(p)
        bot.load_extension(f"{p[:-3]}")

boot_time = time.time()


def _current_version():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except Exception:
        return "unknown"


async def send_startup_ping():
    try:
        row = db.load_second_table_idd(9)
        data = row.get("data", {})
        channel_id = data.get("startup_ping_channel")
        if not channel_id:
            return

        channel = bot.get_channel(int(channel_id))
        if channel is None:
            channel = await bot.fetch_channel(int(channel_id))

        version = _current_version()
        await channel.send(f"⚙️ Build: `{version}`")
    except Exception as exc:
        print(f"[WARN] Startup ping failed: {exc}")

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}, id: {bot.user.id}")
    print(
        f"Setup time: {round((setup_time-start_time),4)} s,Start time: {round((boot_time-setup_time),4)} s"
    )
    if not status_swap.is_running():
        status_swap.start()
    if not bot.startup_ping_sent:
        bot.startup_ping_sent = True
        await send_startup_ping()


bot.run(token)
