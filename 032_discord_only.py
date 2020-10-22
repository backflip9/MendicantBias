import commands
import os
import discord
import sys
from discord.ext.commands import Bot

print(discord.__version__)
mb = Bot(command_prefix='!') # Creates the main bot object - asynchronous
TOKEN = open("TOKEN.txt", "r").readline() # reads the token used by the bot from the local directory

## Flags - Used to turn conditional behaviors on or off - crude, and should upgrade functionality
RELAY = False
RACE = False

@mb.event
async def on_message(message):
	### This needs to STOP - gotta find a way to make this cleaner
	### Numerous behaviors based on conditions present in any message the bot has access to - some memes, some links, some tools

  msg_content = await commands.find(message.content.lower()[1:])
  if(msg_content is not None):
    if(isinstance(msg_content, discord.Embed)):
        await message.channel.send(embed=msg_content)
    else:
        await message.channel.send(msg_content)

@mb.event
async def on_ready():
    if(len(sys.argv) == 2 and sys.argv[1] in commands.scheduled):
        await getattr(commands, sys.argv[1])(mb)
        os._exit(0)

'''
mb.loop.create_task(raceCountdown())
mb.loop.create_task(lookForRecord())
mb.loop.create_task(maintainTwitchNotifs())
'''
mb.run(TOKEN)
