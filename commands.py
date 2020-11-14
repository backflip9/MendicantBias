from time import gmtime, strftime
import os
import requests
import json
from time import sleep
from dateutil import parser
import sched, time
import asyncio
import discord
from discord.ext.commands import Bot
import csv
import sys
import datetime
import time
import math
import json, math, discord

RELAY = False
RACE = False
COMMANDS_FILE = 'commands.json'
CONFIG_FILE = 'config.json'
for key, value in json.loads(open(CONFIG_FILE, 'r').read()).items():
    globals()[key] = value

async def apiRecentWRs():
	### Returns the most recent records list, and replaces the locally stored records list with a new one.
	###NOTE: this means there is no aggregation over time - leaving that to HaloRuns.com

	records = requests.get(str(ENDPOINT + "records/recent" + "/12")).json()
	file = open("records.json", "w+")
	json.dump(records, file)
	file.truncate()
	file.close()
	return records

async def savedRecentWRs():
	### Returns the locally stored records list, or creates one from the haloruns API if not present before returning

	try:
		oldRecords = json.load(open("records.json", "r"))
	except :
		oldRecords = apiRecentWRs()
		print("reset recent world records")
	return oldRecords


async def announce(mb, record):
	### Announces a new record, according to the announcement string; Hoping to add time the previous record stood, as well as what rank in Oldest Records it was

	#record["vid"] = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" test vid link, dont think we need it anymore

	recordsChannel = mb.get_channel(RECORDS_CHANNEL_ID)
	#try:
	# new method, trying to be cleaner about what data is being used; hopefully to be cleaned up more, maybe learn to create better objects for less json
	prev_record = record["prev_record"]#better to split the previous record before messing with the json,^ again might wanna learn objects
	game = record["game_name"]
	diff = record["difficulty_name"]
	level = record["level_name"]
	coop = isCoop(record)
	levelUrl = record["il_board_url"]
	runTime = record["time"]
	vidUrl = record["vid"]
	players = parsePlayers(record)
	prevRunTime = prev_record["time"]
	prevVidUrl = prev_record["vid"]
	prevPlayers = parsePlayers(prev_record)
	timeDiff = str(convertTimes(record["prev_record"]["run_time"]-record["run_time"]))
	prevTimeStanding = getTimeStood(record, prev_record)
	oldestRank = findOldestRank(prev_record)
	#split announcement for ease of printing, logging
	announcement = f":trophy: **new record!**\n{game} {diff} - [{level} {coop}]({levelUrl}) | [{runTime}]({vidUrl})\nset by: {players}\n\nPrevious Record:\n[{prevRunTime}]({prevVidUrl}) by {prevPlayers}\nbeaten by {timeDiff}\nStood for {prevTimeStanding}, it was the {oldestRank} oldest record"
	print(announcement)
	embedlink = discord.Embed(description=announcement, color=0xff0000)
		# old working method but ugly # embedlink = discord.Embed(description=":trophy: **new record!**\n%s %s - [%s %s](%s) | [%s](%s)\nset by: %s\n\nprevious record:\n[%s](%s) by %s\nbeaten by %s" % (record["game_name"], record["difficulty_name"], record["level_name"], iscoop(record), record["il_board_url"], record["time"], str(record["vid"]), parseplayers(record), record["prev_record"]["time"], str(record["prev_record"]["vid"]), parseplayers(record["prev_record"]), str(converttimes(record["prev_record"]["run_time"]-record["run_time"]))), color=0xff0000)
	#except:
	#	embedLink = discord.Embed(description=":trophy: **New Record!**\n%s %s - [%s %s](%s) | [%s](%s)\nSet by: %s" % (record["game_name"], record["difficulty_name"], record["level_name"], isCoop(record), record["il_board_url"], record["time"], str(record["vid"]), parsePlayers(record)), color=0xFF0000)
	try:
		await recordsChannel.send(embed=embedLink)
	except:
		print("record announcement failed")

async def maintainTwitchNotifs(mb):
	### Adds any streams in the current stream list that are not present in the #live-streams channel
	### Then it calls the function to remove what doesn't belong any longer
	### This ought to be changed almost entirely, i hate looking at this abomination

        streams = []
        print("looking for streams to post")
        responses = []
        postedStreamList = []
#        try:
        streamsData = requests.get(str(ENDPOINT + "streams"))
        try:
                streams = streamsData.json()
        except:
                print("LOGGING", "[" + str(time.ctime())[:-5] + "]" + " | STREAM UPDATE FAILURE\n")
                log = open("log.txt", "a")
                log_string = "[" + str(time.ctime())[:-5] + "]" + " | STREAM UPDATE FAILURE\n"
                log.write(log_string, str(streamsData))
                log.close()
        log = open("log.txt", "a")
        print("LOGGING", "[" + str(time.ctime())[:-5] + "]" + " | STREAM UPDATE\n")
        log_string = "[" + str(time.ctime())[:-5] + "]" + " | STREAM UPDATE\n"
        log.write(log_string)
#        print(streams)
        for stream in streams:
                log.write(str(stream["stream"] + "\n"))
        log.close()
#        except:
#            print("stream pull failed")
        postedStreams = await mb.get_channel(NOTIFS_CHANNEL_ID).history(oldest_first = True).flatten()
        postedStreams = postedStreams[1:]
        for stream in postedStreams:
                postedStreamList.append(stream.content)
#        try:
        if streams != []:
#            config = loadConfig()
                for stream in streams:
                        if stream["stream"] not in postedStreamList:
#                        if config[stream["#" + "stream".lower()]]["muted"] == False:
                                responses.append(stream["stream"])
                streamsChannel = mb.get_channel(NOTIFS_CHANNEL_ID)
                if responses != "":
                        for response in responses:
                                        await streamsChannel.send(response)
#        except:
#            print("Failed posting new streams")
        parsedStreams = []
        for stream in streams:
                parsedStreams.append(stream["stream"])
        await purgeNotStreams(mb, parsedStreams)

async def purgeNotStreams(mb, streams):
	### Removes any streams present in the #live-streams channel that are not in the current stream list

	flat = await mb.get_channel(NOTIFS_CHANNEL_ID).history(oldest_first=True).flatten() # returns a flattened ordered list of all present messages in the channel
#    await relayCountdown() # idek lol, think this is here because the channel could flicker if not checked before removal of streams
	oldestMessage = flat[0] # this identifies the top message, because it's used for ^ periodic messages
	if streams != []:
		for stream in streams:
			stream = stream.rstrip()
		for messageObject in flat:
			if messageObject == oldestMessage:
				if messageObject.content != SOME_STREAMS_TEXT:   
					if RELAY==False:
						print("Streams found, editing top message")
						await messageObject.edit(content = SOME_STREAMS_TEXT)
				else:
					print("Found streams, continuing...")
			if messageObject.content not in streams:
				if messageObject == oldestMessage:
					pass
				else:
					await messageObject.delete()
					
	else:
		print("No Streams found, editing top message")
		messagesLen = len(flat)
		for messageObject in flat:
			if messageObject == oldestMessage:
				if RELAY==False:
					await messageObject.edit(content=NO_STREAMS_TEXT)
			else:
				await messageObject.delete()
async def lookForRecord(mb):
	### Upon a new record being added to the HR database, this catches it by checking the API against the locally stored records
	### It then calls the announce() function to push it to the Discord channel

        #try:
        oldRecords = await savedRecentWRs()
        print("checking records")
        newRecords = await apiRecentWRs()
        ids = []
        for element in oldRecords:
                ids.append(element["id"])
        for record in newRecords:
                if record['id'] not in ids:
                        print("announcing!")
                        await announce(mb, record)
        #except:
        #	pass

#wackee's method
#def convertTimes(seconds): 
#	seconds = seconds % (24 * 3600) 
#	hour = seconds // 3600
#	seconds %= 3600
#	minutes = seconds // 60
#	seconds %= 60
#	if hour == 0:
#		if minutes == 00:
#			return ":%02d" % (seconds)
#		else:
#			return "%02d:%02d" % (minutes, seconds)
#	else:
#		return "%d:%02d:%02d" % (hour, minutes, seconds)

# Backflip's method
#Wackee - NOTE: unlikely, but wouldn't this break if there's over an hour timesave?
def convertTimes(seconds):
        return '%d:%02d' % (seconds // 60 if seconds > 60 else 0, seconds % 60)

def isCoop(record):
	return 'Co-op' if record["is_coop"] else 'Solo'

def findOldestRank(record):
	### Returns the rank describing how old the record is
	#Backflip's suggestion:
	#return len(list(filter(lambda pastRecord: pastRecord["timestamp"] <= record["timestamp"], requests.get(str(ENDPOINT + "records/oldest")).json()))) + 1
	try:
		recordsByOldest = requests.get(str(ENDPOINT + "records/oldest")).json()
		for index, item in enumerate(recordsByOldest, 1): # clever optional argument to help with ordinalizing
			if record["timestamp"] <= item["timestamp"]:
				return index
	except:
		print("W E L L - oldest rank check failed")

def buildPlayerMD(player):
	print(str("[%s](https://haloruns.com/profiles/%s)" % (player, player)))
	return str("[%s](https://haloruns.com/profiles/%s)" % (player, player))
	
def parsePlayers(record):
	players = []
	for player in record["runners"]:
		if player != None:
			players.append(buildPlayerMD(player))
	return " | ".join(players)
async def getPoints(pb, wr):
	### Returns the description field for the ".points" command
	### FIX: make this work either way, and with hours

	print("checking points", pb, wr)
	pb_split = pb.split(":")
	pb_mins = int(pb_split[0])
	pb_secs = int(pb_split[1])
	pb_comb = pb_secs + 60 * pb_mins
	wr_split = wr.split(":")
	wr_mins = int(wr_split[0])
	wr_secs = int(wr_split[1])
	wr_comb = wr_secs + 60 * wr_mins
	points = round((0.008 * math.exp(4.8284*(wr_comb/pb_comb)) * 100), 1)
	print(points)
	help_string = "Use like this: .points [pb]mm:ss [wr]mm:ss .\nIf you are comparing a full game, fit hours to minutes please.\n"
	print(str("Your PB of " + pb + " against "  + wr + " is worth " + str(points) + " points"))
	return(str(help_string + "Your PB of " + pb + " against "  + wr + " is worth " + str(points) + " points"))

def getTimeStood(record, prev_record):
	secs = record["timestamp"] - prev_record["timestamp"]
	days = secs//86400
	hours = (secs - days*86400)//3600
	minutes = (secs - days*86400 - hours*3600)//60
	seconds = secs - days*86400 - hours*3600 - minutes*60
	result = ("{0} day{1}, ".format(days, "s" if days!=1 else "") if days else "") + \
	("{0} hour{1}, ".format(hours, "s" if hours!=1 else "") if hours else "") + \
	("{0} minute{1}, ".format(minutes, "s" if minutes!=1 else "") if minutes else "") + \
	("{0} second{1}, ".format(seconds, "s" if seconds!=1 else "") if seconds else "")
	return result

def ordinalize(rank):
	# I'm checking for 10-20 because those are the digits that
	# don't follow the normal counting scheme. 
	if ((rank % 100) // 2) == 1:
		suffix = 'th'
	else:
		# the second parameter is a default.
		suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(rank % 10, 'th')
	return str(rank) + suffix

async def raceCountdown(ret=False):
	### Replaces the top message in #live-streams with a countdown to an event, if RACE is set

	dt = datetime.datetime
	raceStartTime = dt(year=2020, month=8, day=25, hour=15)
	if ret == True:
		flat = await mb.get_channel(NOTIFS_CHANNEL_ID).history(oldest_first=True).flatten()
		now = dt.now()
		delta = raceStartTime - now
		return str(':'.join(str(delta).split(':')[:2])) + " until the HSL A1 Race begins!\nWatch [Here](https://www.twitch.tv/HaloRaces)"
	while True:
		await asyncio.sleep(10)
		if RACE==True:
			flat = await mb.get_channel(NOTIFS_CHANNEL_ID).history(oldest_first=True).flatten()
			now = dt.now()
			delta = raceStartTime - now
			oldestMessage = flat[0]            
			await oldestMessage.edit(content = str(':'.join(str(delta).split(':')[:2])) + " until the HSL A1 Race!")


async def race(_):
    if RACE == True:
        w = await raceCountdown(ret=True)
        return w
    else:
        return None

async def points(message):
    args = message.lower().split()
    if len(args) == 3:
        points = await getPoints(args[1], args[2])
        return discord.Embed(title="Points Calculator", description=points)
    else:
        return None

def calc(message):
    print('message')
    game_abbreviations = { k:([k] + {"hce": ["h1", "ce"]}.get(k, list())) for k in ["reach", "hce", "h2", "h2a", "h3", "odst", "h4", "h5"] }
    matches = list(filter(lambda x: message.lower().split()[1] in x[1], game_abbreviations.items()))
    return f"https://haloruns.com/timeCalc/{matches[0][0]}" if len(matches) > 0 else None

async def find(txt):
    txt_result = json.loads(open(COMMANDS_FILE).read()).get(txt, None)
    if(txt_result):
        return txt_result
    func_name = txt.split(' ')[0]
    return await globals()[func_name](txt) if func_name in ['race', 'points', 'calc'] else None

scheduled = [ raceCountdown, lookForRecord, maintainTwitchNotifs ]
