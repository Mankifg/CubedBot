from pathlib import Path
from itertools import cycle
import json
import os
from itertools import cycle
from dotenv import load_dotenv
import time
import discord
from discord.ext import tasks, commands

start_time = time.time()

load_dotenv()
token = os.getenv("TOKEN")

status = cycle(
    [
        "Made by Mankifg",
        "Some commands are used, because we can't trust the calendar.",
    ]
)

@tasks.loop(seconds=10)
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

setup_time = time.time()

if __name__ == "__main__":
    for path in Path("./src/Cogs").rglob("*.py"):

        p = str(path)
        p = p.replace("\\", ".")
        p = p.replace("/", ".")
        print(p)
        bot.load_extension(f"{p[:-3]}")

boot_time = time.time()

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}, id: {bot.user.id}")
    with open("settings.json","r") as f:
        print(json.load(f))
    print(
        f"Setup time: {round((setup_time-start_time),4)} s,Start time: {round((boot_time-setup_time),4)} s"
    )
    if not status_swap.is_running():
        status_swap.start()


bot.run(token)
