#!/usr/bin/python3

#Meier benched: https://www.tsn.ca/nhl/insider-trading-new-jersey-devils-timo-meier-benching-sends-clear-message-to-team-1.2022333

#Jacob MacDonald (D) as a winger

#Poitras benched in third period of 2023/02/0408 vs ARIs "to manage workload"
#Poitras healthy scratch in 0392 vs BUF "to manage workload"
#Poitras needs shorter shifts (44s in 25 games was 6th longest among forwards), Beecher at lowest 39s

#11-7
#https://thehockeywriters.com/jon-cooper-thanking-heaven-for-11-7/
#https://www.reddit.com/r/leafs/comments/2k14g8/11_forwards_7_defensemen/
#https://www.stltoday.com/sports/hockey/professional/blues-learning-to-live-with-11-forwards-seven-defensemen/article_5b5bc4cb-b565-5658-b134-4805dca1bafb.html
#https://thehockeywriters.com/winnipeg-jets-11-forwards-7-defensemen-2021-22/


import os
import sys
import datetime
import requests
import json
import time
import re
import math
from unidecode import unidecode
from bs4 import BeautifulSoup,NavigableString,Tag

def undectime(time):
	s=int(time) % 60
	m=int((time-s)/60)
	m=m % 20
	return "{m:02}:{s:02}".format(m=m, s=s)

def decimaltime(time, period=0):
	ra=re.split(':', time)
	t=0
	n=0
	while len(ra) > 0:
		if n == 0:
			t=t+int(ra[-1])
		elif n == 1:
			t=t+(int(ra[-1])*60)
		elif n == 2:
			t=t+(int(ra[-1])*20)
		ra.pop()
		n=n+1

	if period != 0:
		period=float(period)
		t = t + (period/100.0)
		t = t + (period-1)*1200

	return t

def get_game_prefix():
	gamedir=os.getcwd()
	return gamedir

def get_game_path(season, season_type, gamenum):
	gamedir=get_game_prefix()+os.sep+str(season)+os.sep+str(season_type)
	gamepath=gamedir+os.sep+str(gamenum)

	return gamepath

def write_game(game):
	season=game['GAME']['html']['y']
	season_type=game['GAME']['html']['t']
	gamenum=game['GAME']['html']['n']
	gamepath=get_game_path(season, season_type, gamenum)
	writestr=json.dumps(game)
	try:
		f=open(gamepath, 'w')
		f.write(writestr)
		f.close()
	except Exception as e:
		print(e)
		exit(1)

def read_game(season, season_type, gamenum):
	game=None
	gamepath=get_game_path(season, season_type, gamenum)
	try:
		f=open(gamepath)
		game=f.readlines()
		f.close()
	except FileNotFoundError as e:
		print(e)
		return game
	except Exception as e:
		print(e)
		exit(1)
	
	game=''.join(game)
	game=json.loads(game)
	return game

def makelineinfo(game, team, linekey):
	debug=False
	if debug:
		print("   New line!  "+linekey)
	lineinfo={}
	lineinfo['key']=linekey
	lineinfo['team']=team
	lineinfo['situation']={}
	lineinfo['shifts']=[]
	lineinfo['toi']=0
	game['lines'][team]['line'][linekey]=lineinfo

	game=make_positions(game, team, linekey)
	return game

def end_line(game, playi, team=None):
	debug=False

	if playi >= len(game['plays']):
		playi=len(game['plays'])-1

	if playi < 0:
		f=open("/tmp/"+game['gamePk'], 'w')
		f.write(json.dumps(game))
		f.close()
		return game

	play = game['plays'][playi]

	if team is None:
		if 'Team' in play:
			team = play['Team']

	if game['lines'][team]['last']['line'] == -1:
		return game
	oldshifti=game['lines'][team]['last']['line']

	otherteam=None
	for teampos in game['teams']:
		if game['teams'][teampos]['abv'] != team:
			otherteam=game['teams'][teampos]['abv']
			break

	oldshift = game['lines']['shifts']['line'][oldshifti]

	oldshift['end']=playi
	oldshift['enddt']=play['dt']
	oldshift['toi']=int(oldshift['enddt'])-int(oldshift['startdt'])

	if oldshift['toi'] == 0:
		if debug:
			print("   Eliminating shift #"+str(oldshifti)+" for "+oldshift['key']+" at play "+str(playi)+" dt "+str(play['dt']))

		if 'last' in oldshift:
			if 'next' in game['lines']['shifts']['line'][oldshift['last']]:
				del(game['lines']['shifts']['line'][oldshift['last']]['next'])
			game['lines'][team]['last']['line']=oldshift['last']
		else:
			game['lines'][team]['last']['line']=-1
#		sys.stdin.readline()

		return game

	if debug:
		print("   Ending shift #"+str(oldshifti)+" for "+oldshift['key']+" at play "+str(playi)+" dt "+str(play['dt']))

	for strplayi in range(oldshift['start'], oldshift['end']+1):
		strplay=game['plays'][strplayi]
		playstr=str(len(list(strplay[team]['onice'])))+'v'+str(len(list(strplay[otherteam]['onice'])))
		if len(oldshift['segments']) > 0:
			if oldshift['segments'][-1]['strength'] == playstr:
				continue
			oldsegment=oldshift['segments'][-1]
			oldsegment['end']=strplayi-1
			oldsegment['enddt']=strplay['dt']
			oldsegment['toi']=int(oldsegment['enddt'])-int(oldsegment['startdt'])
			oldshift['segments'][-1]=oldsegment

		newsegment={}
		newsegment['shift']=oldshifti
		newsegment['strength']=playstr
		newsegment['start']=strplayi
		newsegment['startdt']=strplay['dt']
		oldshift['segments'].append(newsegment)

	if len(oldshift['segments']) > 0:
		if 'end' not in oldshift['segments'][-1]:
			strplay=game['plays'][oldshift['end']]
			oldsegment=oldshift['segments'][-1]
			oldsegment['end']=len(game['plays'])-1
			oldsegment['enddt']=strplay['dt']
			oldsegment['toi']=int(oldsegment['enddt'])-int(oldsegment['startdt'])
			oldshift['segments'][-1]=oldsegment

	if len(oldshift['segments']) > 1:
		if debug:
			print("Shift "+str(oldshifti))
			segmenti=0
			while segmenti < len(oldshift['segments']):
				segment=oldshift['segments'][segmenti]
				print("   "+str(segmenti)+" "+str(segment['startdt'])+" - "+str(segment['enddt'])+" at "+segment['strength'])
				segmenti=segmenti+1

			print("   ---")

		segmenti=0
		while segmenti < len(oldshift['segments']):
			segment=oldshift['segments'][segmenti]
			if debug:
				print("   "+str(segmenti)+" "+str(segment['startdt'])+" - "+str(segment['enddt'])+" = "+str(segment['toi'])+" at "+segment['strength'])
			if segmenti > 0:
				lastsegment=oldshift['segments'][segmenti-1]
				if segment['toi'] == 0 or segment['strength'] == lastsegment['strength']:
					if debug:
						print("      Absorbing last "+str(segmenti-1)+" "+str(lastsegment['startdt'])+" - "+str(lastsegment['enddt'])+" = "+str(lastsegment['toi'])+" at "+lastsegment['strength'])
					for k in ['end', 'enddt']:
						lastsegment[k]=segment[k]
					lastsegment['toi']=int(lastsegment['enddt'])-int(lastsegment['startdt'])
					oldshift['segments'][segmenti-1]=lastsegment
					oldshift['segments'].pop(segmenti)
					continue

			if segmenti < len(oldshift['segments'])-1:
				nextsegment=oldshift['segments'][segmenti+1]
				if segment['toi'] == 0 or segment['strength'] == nextsegment['strength']:
					if debug:
						print("      Absorbing into next "+str(segmenti+1)+" "+str(nextsegment['startdt'])+" - "+str(nextsegment['enddt'])+" = "+str(nextsegment['toi'])+" at "+nextsegment['strength'])
					for k in ['start', 'startdt']:
						nextsegment[k]=segment[k]
					segment['toi']=int(nextsegment['enddt'])-int(nextsegment['startdt'])
					oldshift['segments'][segmenti+1]=nextsegment
					oldshift['segments'].pop(segmenti)
					continue

			segmenti=segmenti+1

		if debug:
			print("   ===")
			segmenti=0
			while segmenti < len(oldshift['segments']):
				segment=oldshift['segments'][segmenti]
				print("   "+str(segmenti)+" "+str(segment['startdt'])+" - "+str(segment['enddt'])+" at "+segment['strength'])
				segmenti=segmenti+1

	for part in ['fline', 'dline', 'goalie']:
		key=game['lines'][team]['line'][oldshift['key']][part+'key']

	game['lines']['shifts']['line'][oldshifti]=oldshift

	return game

def make_positions(game, team, linekey, oldpositions={}):
	positions={}
	for pos in ['LW', 'C', 'RW', 'LD', 'RD', 'G']:
		positions[pos]=[]

	if linekey == '':
		game['lines'][team]['line'][linekey]['positions']=positions
		return game

	unknownd=[]
	unknownf=[]
	players=linekey.split(',')
	for nhlid in players:
		player=game['players'][nhlid]
		pos=player['Position']

		if pos == 'F':
			if 'Hand' in player:
				pos=player['Hand']+'W'
			else:
				unknownf.append(nhlid)
				continue
		elif pos == 'D':
			if 'Hand' in player:
				pos=player['Hand']+'D'
			else:
				unknownd.append(nhlid)
				continue
		elif pos == 'L':
			pos='LW'
		elif pos == 'R':
			pos='RW'

		game['players'][nhlid]['Position']=pos
		if pos not in positions:
			positions[pos]=[nhlid]
		else:
			positions[pos].append(nhlid)

	for nhlid in unknownf:
		if 'C' not in positions:
			positions['C']=[]
		game['players'][nhlid]['Position']='C'
		positions['C'].append(nhlid)
	
	for nhlid in unknownd:
		if 'RD' not in positions:
			game['players'][nhlid]['Position']='RD'
			positions['RD']=[nhlid]
		elif 'LD' not in positions:
			game['players'][nhlid]['Position']='LD'
			positions['LD']=[nhlid]
		else:
			game['players'][nhlid]['Position']='RD'
			positions['RD'].append(nhlid)

	game['lines'][team]['line'][linekey]['positions']=positions
	return game

def start_line(game, playi):
	debug=False

	play=game['plays'][playi]
	team=play['Team']
	linera=sorted(list(play[team]['onice']))
	linekey=','.join(linera)
	if linekey not in game['lines'][team]['line']:
		game=makelineinfo(game, team, linekey)
	newshift={}
	newshift['start']=playi
	newshift['startdt']=play['dt']
	newshift['team']=team
	newshift['key']=linekey
	newshift['segments']=[]
	newshifti=len(game['lines']['shifts']['line'])

	if debug:
		print("   Starting shift #"+str(newshifti)+" for "+team+" "+linekey+" at play "+str(playi)+" dt "+str(play['dt']))


	if game['lines'][team]['last']['line'] != -1:
		oldshifti=game['lines'][team]['last']['line']
		oldshift=game['lines']['shifts']['line'][oldshifti]
		oldshift['next']=newshifti
		game['lines']['shifts']['line'][oldshifti]=oldshift

		newshift['last']=oldshifti

	game['lines']['shifts']['line'].append(newshift)
	game['lines'][team]['last']['line']=newshifti

	game=create_part_lines(game, team, newshifti)
	lineinfo=game['lines'][team]['line'][linekey]
	for part in ['fline', 'dline', 'goalie']:
		if 'last' in newshift:
			oldshifti=newshift['last']
			oldshift=game['lines']['shifts']['line'][oldshifti]
			oldlineinfo=game['lines'][team]['line'][oldshift['key']]
			if oldlineinfo[part+'key'] == lineinfo[part+'key']:
				continue
			game=end_part_line(game, team, part, oldshifti)

		game=start_part_line(game, team, part, newshifti)

	return game

def start_part_line(game, team, part, lineshifti):
	#game['lines']['shifts']['line'].append(newshift)
	lineshift=game['lines']['shifts']['line'][lineshifti]
	lineinfo=game['lines'][team]['line'][lineshift['key']]
	partkey=lineinfo[part+'key']
	partinfo=None
	if partkey not in game['lines'][team][part]:
		partinfo={}
		partinfo['key']=partkey
		partinfo['team']=team
		partinfo['toi']=0
		partinfo['str']=lineinfo[part+'str']
		partinfo['id']=lineinfo[part+'id']
		partinfo['shifts']=[]
		partinfo['positions']={}
		partinfo['final']={}
		for pos in ['LW', 'C', 'RW', 'F', 'XF', 'XF2', 'XF3', 'XF4', 'XF5', 'XF6']:
			partinfo['positions'][pos]=lineinfo['positions'][pos]
			partinfo['final'][pos]=lineinfo['final'][pos]

	else:
		partinfo=game['lines'][team][part][partkey]

	partshift={}
	partshift['start']=lineshift['start']
	partshift['startdt']=lineshift['startdt']
	partshift['startline']=lineshifti
	partshift['team']=team
	partshift['key']=partkey
	partshift['segments']=[]
	partshift['type']=part
	if game['lines'][team]['last'][part] != -1:
		partshift['last']=game['lines'][team]['last'][part]
		game['lines']['shifts'][part][partshift['last']]['next']=len(game['lines']['shifts'][part])
	
	game['lines'][team]['last'][part]=len(game['lines']['shifts'][part])
	game['lines']['shifts'][part].append(partshift)
	game['lines'][team][part][partkey]=partinfo
	return game


def end_part_line(game, team, part, lineshifti):
	partshifti=game['lines'][team]['last'][part]
	if partshifti == -1:
		return game
	partshift=game['lines']['shifts'][part][partshifti]
	partinfo=game['lines'][team][part][partshift['key']]

	partshift['endline']=lineshifti
	partshift['enddt']=game['lines']['shifts']['line'][lineshifti]['enddt']
	partshift['toi']=int(partshift['enddt'])-int(partshift['startdt'])
	partshift['end']=game['lines']['shifts']['line'][lineshifti]['end']

	segmentlinei=partshift['startline']
	while segmentlinei <= partshift['end']:
		lineshift=game['lines']['shifts']['line'][segmentlinei]
		for segment in lineshift['segments']:
			partshift['segments'].append(segment)
		if 'next' not in lineshift:
			break
		segmentlinei=lineshift['next']

	game['lines']['shifts'][part][partshifti]=partshift
	game['lines'][team][part][partshift['key']]=partinfo

	return game

def create_part_lines_from_scratch(game, team, key):
	debug=False
	lineinfo=game['lines'][team]['line'][key]
	if 'str' not in lineinfo:
		newpos={}
		surplus=[]

		scratchpos=json.loads(json.dumps(lineinfo['positions']))

		#Do we have faceoff intel on this line?  Use it!
		if 'MakeC' in lineinfo:
			for pos in scratchpos:
				playeri=0
				while playeri < len(scratchpos[pos]):
					if scratchpos[pos][playeri] == lineinfo['MakeC']:
						if debug:
							print("   "+str(scratchpos[k][i])+" ("+get_name(game, scratchpos[k][i])+") "+pos+" -> C from MakeC")
						scratchpos[pos].pop(playeri)
						continue
					playeri=player+1
			if 'C' not in scratchpos:
				scratchpos['C']=[]
			scratchpos['C'].insert(0, lineinfo['MakeC'])
						
		#Remove surplus position calls
		for pos in ['LW', 'C', 'RW', 'LD', 'RD', 'G']:
			if pos not in scratchpos or len(scratchpos[pos]) == 0:
				continue
			while len(scratchpos[pos]) > 1:
				surplus.append(scratchpos[pos].pop())
				if debug:
					print("   "+str(surplus[-1])+" ("+get_name(game, surplus[-1])+") is a surplus "+pos)
				continue

		#Assign single position calls
		for pos in ['LW', 'C', 'RW', 'LD', 'RD', 'G']:
			if pos not in scratchpos or len(scratchpos[pos]) == 0:
				continue
			newpos[pos]=scratchpos[pos][0]
			if debug:
				print("   "+pos+" == "+str(newpos[pos])+" ("+get_name(game, newpos[pos])+")")

		#Take a series of wild guesses where people are supposed to go
		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			posra=[]
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=[playerinfo['Hand']+'W']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=[playerinfo['Hand']+'D']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by position & hand")
				continue

			playeri=playeri+1

		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			posra=[]
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=['C', 'LW', 'RW']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=['LD', 'RD']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by position")
				continue

			playeri=playeri+1

		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=[playerinfo['Hand']+'D']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=[playerinfo['Hand']+'W']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by hand")
				continue

			playeri=playeri+1


		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=['LD', 'RD']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=['LW', 'RW', 'C']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by position")
				continue

			playeri=playeri+1

		playeri=0
		while playeri < len(surplus):
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=['XF', 'XF2', 'XF3', 'XF4', 'XF5', 'XF6']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=['XD', 'XD2', 'XD3', 'XD4', 'XD5', 'XD6']
			elif playerinfo['Position'] == 'G':
				posra=['XG', 'XG2', 'XG3', 'XG4', 'XG5', 'XG6']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by extra")
				continue

			playeri=playeri+1

		lineinfo['final']=newpos
		lineinfo['str']=[]
		lineinfo['id']=[]
		for pos in ['LW', 'C', 'RW', 'LD', 'RD', 'G']:
			if pos not in newpos:
				continue
			lineinfo['str'].append(get_name(game, newpos[pos]))
			lineinfo['id'].append(newpos[pos])
		for pos in ['XF', 'XF2', 'XF3', 'XF4', 'XF5', 'XF6', 'XD', 'XD2', 'XD3', 'XD4', 'XD5', 'XD6', 'XG', 'XG2', 'XG3', 'XG4', 'XG5', 'XG6']:
			if pos not in newpos:
				continue
			lineinfo['str'].append(get_name(game, newpos[pos]))
			lineinfo['id'].append(newpos[pos])
		lineinfo['key']=','.join(sorted(lineinfo['id']))
		lineinfo['id']=','.join(lineinfo['id'])
		lineinfo['str']=','.join(lineinfo['str'])

		lineinfo['flinestr']=[]
		lineinfo['flineid']=[]
		for pos in ['LW', 'C', 'RW']:
			if pos not in newpos:
				lineinfo['flinestr'].append("")
			else:
				lineinfo['flinestr'].append(get_name(game, newpos[pos]))
				lineinfo['flineid'].append(newpos[pos])
		for pos in ['XF', 'XF2', 'XF3', 'XF4', 'XF5', 'XF6']:
			if pos not in newpos:
				continue
			lineinfo['flinestr'].append(get_name(game, newpos[pos]))
			lineinfo['flineid'].append(newpos[pos])
		lineinfo['flinekey']=','.join(sorted(lineinfo['flineid']))
		lineinfo['flineid']=','.join(lineinfo['flineid'])
		lineinfo['flinestr']=','.join(lineinfo['flinestr'])

		lineinfo['dlinestr']=[]
		lineinfo['dlineid']=[]
		for pos in ['LD', 'RD']:
			if pos not in newpos:
				continue
			lineinfo['dlinestr'].append(get_name(game, newpos[pos]))
			lineinfo['dlineid'].append(newpos[pos])
		for pos in ['XD', 'XD2', 'XD3', 'XD4', 'XD5', 'XD6']:
			if pos not in newpos:
				continue
			lineinfo['dlinestr'].append(get_name(game, newpos[pos]))
			lineinfo['dlineid'].append(newpos[pos])
		lineinfo['dlinekey']=','.join(sorted(lineinfo['dlineid']))
		lineinfo['dlineid']=','.join(lineinfo['dlineid'])
		lineinfo['dlinestr']=','.join(lineinfo['dlinestr'])

		lineinfo['goaliestr']=[]
		lineinfo['goalieid']=[]
		for pos in ['G']:
			if pos not in newpos:
				continue
			lineinfo['goaliestr'].append(get_name(game, newpos[pos]))
			lineinfo['goalieid'].append(newpos[pos])
		for pos in ['XG', 'XG2', 'XG3', 'XG4', 'XG5', 'XG6']:
			if pos not in newpos:
				continue
			lineinfo['goaliestr'].append(get_name(game, newpos[pos]))
			lineinfo['goalieid'].append(newpos[pos])
		lineinfo['goaliekey']=','.join(sorted(lineinfo['goalieid']))
		lineinfo['goalieid']=','.join(lineinfo['goalieid'])
		lineinfo['goaliestr']=','.join(lineinfo['goaliestr'])
		game['lines'][team]['line'][key]=lineinfo

	for part in ['fline', 'dline', 'goalie']:
		key=lineinfo[part+'key']

		if key in game['lines'][team][part]:
			continue

		game['lines'][team][part][key]={}
		game['lines'][team][part][key]['team']=team
		game['lines'][team][part][key]['key']=key
		game['lines'][team][part][key]['str']=lineinfo[part+'str']
		game['lines'][team][part][key]['id']=lineinfo[part+'id']
		game['lines'][team][part][key]['shifts']=[]
		game['lines'][team][part][key]['toi']=0

	if debug:
		print("Created part lines from scratch")
		sys.stdin.readline()

	return game

def create_part_lines(game, team, newshifti):
	debug=False
	shift=game['lines']['shifts']['line'][newshifti]
	lineinfo=game['lines'][team]['line'][shift['key']]
	play=game['plays'][shift['start']]
	if 'str' not in lineinfo:
		newpos={}
		surplus=[]

		scratchpos=json.loads(json.dumps(lineinfo['positions']))
		#This is a losing idea this early in the process!
		#Put players from the last shift where they were before unless they're
		#   the only ones filling that position.
		#if 'last' in shift and False:
		#	oldshift=game['lines']['shifts']['line'][shift['last']]
		#	oldlineinfo=game['lines'][team]['line'][oldshift['key']]
		#	for pos in oldlineinfo['final']:
		#		if oldlineinfo['final'][pos] not in play[team]['onice']:
		#			continue
		#		for k in scratchpos:
		#			i=0
		#			while i < len(scratchpos[k]):
		#				if scratchpos[k][i] is not None and scratchpos[k][i] == oldlineinfo['final'][pos]:
		#					if k != pos and debug:
		#						print("   "+str(scratchpos[k][i])+" ("+get_name(game, scratchpos[k][i])+") "+k+" -> "+pos+" from past")
		#					scratchpos[k].pop(i)
		#					continue
		#				i=i+1
		#		if pos not in scratchpos:
		#			scratchpos[pos]=[]
		#		scratchpos[pos].insert(0, oldlineinfo['final'][pos])

		#Do we have faceoff intel on this line?  Use it!
		if 'MakeC' in lineinfo:
			for pos in scratchpos:
				playeri=0
				while playeri < len(scratchpos[pos]):
					if scratchpos[pos][playeri] == lineinfo['MakeC'] and debug:
						print("   "+str(scratchpos[k][i])+" ("+get_name(game, scratchpos[k][i])+") "+pos+" -> C from MakeC")
						scratchpos[pos].pop(playeri)
						continue
					playeri=player+1
			if 'C' not in scratchpos:
				scratchpos['C']=[]
			scratchpos['C'].insert(0, lineinfo['MakeC'])
						
		#Remove surplus position calls
		for pos in ['LW', 'C', 'RW', 'LD', 'RD', 'G']:
			if pos not in scratchpos or len(scratchpos[pos]) == 0:
				continue
			while len(scratchpos[pos]) > 1:
				surplus.append(scratchpos[pos].pop())
				if debug:
					print("   "+str(surplus[-1])+" ("+get_name(game, surplus[-1])+") is a surplus "+pos)
				continue

		#Put players from the last shift where they were before if there's no
		#   better option
		if 'last' in shift and False:
			oldshift=game['lines']['shifts']['line'][shift['last']]
			oldlineinfo=game['lines'][team]['line'][oldshift['key']]
			for surplusi in range(len(surplus)-1, -1, -1):
				for pos in oldlineinfo['final']:
					if len(scratchpos[pos]) > 0:
						continue
					if oldlineinfo['final'][pos] != surplus[surplusi]:
						continue
					print("   "+str(surplus[surplusi])+" ("+get_name(game, surplus[surplusi])+") "+pos+" from past")
					scratchpos[pos].insert(0, surplus[surplusi])
					surplus.pop(surplusi)

		#Assign single position calls
		for pos in ['LW', 'C', 'RW', 'LD', 'RD', 'G']:
			if pos not in scratchpos or len(scratchpos[pos]) == 0:
				continue
			newpos[pos]=scratchpos[pos][0]
			if debug:
				print("   "+pos+" == "+str(newpos[pos])+" ("+get_name(game, newpos[pos])+")")

		#Take a series of wild guesses where people are supposed to go
		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			posra=[]
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=[playerinfo['Hand']+'W']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=[playerinfo['Hand']+'D']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by position & hand")
				continue

			playeri=playeri+1

		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			posra=[]
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=['C', 'LW', 'RW']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=['LD', 'RD']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by position")
				continue

			playeri=playeri+1

		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=[playerinfo['Hand']+'D']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=[playerinfo['Hand']+'W']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by hand")
				continue

			playeri=playeri+1


		playeri=0
		while playeri < len(surplus):
			nhlid=surplus[playeri]
			playerinfo=game['players'][nhlid]
			usepos=None
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=['LD', 'RD']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=['LW', 'RW', 'C']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by position")
				continue

			playeri=playeri+1

		playeri=0
		while playeri < len(surplus):
			if playerinfo['Position'] == 'LW' or playerinfo['Position'] == 'C' or playerinfo['Position'] == 'RW':
				posra=['XF', 'XF2', 'XF3', 'XF4', 'XF5', 'XF6']
			elif playerinfo['Position'] == 'LD' or playerinfo['Position'] == 'RD':
				posra=['XD', 'XD2', 'XD3', 'XD4', 'XD5', 'XD6']
			elif playerinfo['Position'] == 'G':
				posra=['XG', 'XG2', 'XG3', 'XG4', 'XG5', 'XG6']

			for pos in posra:
				if pos not in newpos:
					usepos=pos
					break

			if usepos is not None:
				newpos[usepos]=surplus[playeri]
				surplus.pop(playeri)
				if debug:
					print("   "+usepos+" == "+str(newpos[usepos])+" ("+get_name(game, newpos[usepos])+") by extra")
				continue

			playeri=playeri+1

		lineinfo['final']=newpos
		lineinfo['str']=[]
		lineinfo['id']=[]
		for pos in ['LW', 'C', 'RW', 'LD', 'RD', 'G']:
			if pos not in newpos:
				continue
			lineinfo['str'].append(get_name(game, newpos[pos]))
			lineinfo['id'].append(newpos[pos])
		for pos in ['XF', 'XF2', 'XF3', 'XF4', 'XF5', 'XF6', 'XD', 'XD2', 'XD3', 'XD4', 'XD5', 'XD6', 'XG', 'XG2', 'XG3', 'XG4', 'XG5', 'XG6']:
			if pos not in newpos:
				continue
			lineinfo['str'].append(get_name(game, newpos[pos]))
			lineinfo['id'].append(newpos[pos])
		lineinfo['key']=','.join(sorted(lineinfo['id']))
		lineinfo['id']=','.join(lineinfo['id'])
		lineinfo['str']=','.join(lineinfo['str'])

		lineinfo['flinestr']=[]
		lineinfo['flineid']=[]
		for pos in ['LW', 'C', 'RW']:
			if pos not in newpos:
				lineinfo['flinestr'].append("")
			else:
				lineinfo['flinestr'].append(get_name(game, newpos[pos]))
				lineinfo['flineid'].append(newpos[pos])
		for pos in ['XF', 'XF2', 'XF3', 'XF4', 'XF5', 'XF6']:
			if pos not in newpos:
				continue
			lineinfo['flinestr'].append(get_name(game, newpos[pos]))
			lineinfo['flineid'].append(newpos[pos])
		lineinfo['flinekey']=','.join(sorted(lineinfo['flineid']))
		lineinfo['flineid']=','.join(lineinfo['flineid'])
		lineinfo['flinestr']=','.join(lineinfo['flinestr'])

		lineinfo['dlinestr']=[]
		lineinfo['dlineid']=[]
		for pos in ['LD', 'RD']:
			if pos not in newpos:
				continue
			lineinfo['dlinestr'].append(get_name(game, newpos[pos]))
			lineinfo['dlineid'].append(newpos[pos])
		for pos in ['XD', 'XD2', 'XD3', 'XD4', 'XD5', 'XD6']:
			if pos not in newpos:
				continue
			lineinfo['dlinestr'].append(get_name(game, newpos[pos]))
			lineinfo['dlineid'].append(newpos[pos])
		lineinfo['dlinekey']=','.join(sorted(lineinfo['dlineid']))
		lineinfo['dlineid']=','.join(lineinfo['dlineid'])
		lineinfo['dlinestr']=','.join(lineinfo['dlinestr'])

		lineinfo['goaliestr']=[]
		lineinfo['goalieid']=[]
		for pos in ['G']:
			if pos not in newpos:
				continue
			lineinfo['goaliestr'].append(get_name(game, newpos[pos]))
			lineinfo['goalieid'].append(newpos[pos])
		for pos in ['XG', 'XG2', 'XG3', 'XG4', 'XG5', 'XG6']:
			if pos not in newpos:
				continue
			lineinfo['goaliestr'].append(get_name(game, newpos[pos]))
			lineinfo['goalieid'].append(newpos[pos])
		lineinfo['goaliekey']=','.join(sorted(lineinfo['goalieid']))
		lineinfo['goalieid']=','.join(lineinfo['goalieid'])
		lineinfo['goaliestr']=','.join(lineinfo['goaliestr'])
		game['lines'][team]['line'][shift['key']]=lineinfo

	for part in ['fline', 'dline', 'goalie']:
		key=lineinfo[part+'key']

		if key in game['lines'][team][part]:
			continue

		game['lines'][team][part][key]={}
		game['lines'][team][part][key]['team']=team
		game['lines'][team][part][key]['key']=key
		game['lines'][team][part][key]['str']=lineinfo[part+'str']
		game['lines'][team][part][key]['id']=lineinfo[part+'id']
		game['lines'][team][part][key]['shifts']=[]
		game['lines'][team][part][key]['toi']=0

	if debug:
		print("Done with creating parts")
		sys.stdin.readline()

	return game

def get_name(game, nhlid):
	player=game['players'][nhlid]
	return player['Name']

def get_line_str(game, linekey):
	for team in game['lines']:
		for part in ['line', 'fline', 'dline', 'goalie']:
			if linekey not in game['lines'][team]['line']:
				continue
			return game['lines'][team][part][linekey]['str']
	newstr=[]
	for p in linekey.split(','):
		newstr.append(get_name(game, p))
	return ','.join(newstr)

def add_lines(game):
	debug=False
	if 'lines' not in game:
		game['lines']={}
		game['lines']['shifts']={}
		for part in ['line', 'fline', 'dline', 'goalie']:
			game['lines']['shifts'][part]=[]
		for teampos in game['teams']:
			abv=game['teams'][teampos]['abv']
			game['lines'][abv]={}
			game['lines'][abv]['last']={}
			game['lines'][abv]['shifts']={}
			for part in ['line', 'fline', 'dline', 'goalie']:
				game['lines'][abv]['shifts'][part]=[]
				game['lines'][abv]['last'][part]=-1
				game['lines'][abv][part]={}

	for playi in range(0, len(game['plays'])):
		play=game['plays'][playi]
		if debug:
			print(str(play['dt'])+" - "+play['PLEvent'])

		if play['PLEvent'] == 'CHANGE':
			team=play['Team']
			linekey=sorted(list(play[team]['onice']))
			game=end_line(game, playi)
			game=start_line(game, playi)

		elif play['PLEvent'] == 'FAC':
			for teampos in game['teams']:
				fotaker=None
				fotype=None

				abv=game['teams'][teampos]['abv']
				if game['lines'][abv]['last']['line'] == -1:
					continue

				curshifti=game['lines'][abv]['last']['line']
				curshift=game['lines']['shifts']['line'][curshifti]
				lineinfo=game['lines'][abv]['line'][curshift['key']]
				if 'faceoffs' not in lineinfo:
					lineinfo['faceoffs']={}
					lineinfo['faceoffs']['L']={}
					lineinfo['faceoffs']['R']={}
					lineinfo['faceoffs']['C']={}
					lineinfo['faceoffs']['ALL']={}

				fotaker=play['AwayFO'][0]
				if teampos == 'home':
					fotaker=play['HomeFO'][0]

				if 'PXP' in play and 'details' in play['PXP'] and 'yCoord' in play['PXP']['details'] and 'xCoord' in play['PXP']['details']:
					y=play['PXP']['details']['yCoord']
					if y == 0:
						fotype='C'
					elif y > 0:
						if play['PXP']['homeTeamDefendingSide'] == 'left':
							if teampos == 'away':
								fotype='R'
							else:
								fotype='L'
						else:
							if teampos == 'away':
								fotype='L'
							else:
								fotype='R'
					elif y < 0:
						if play['PXP']['homeTeamDefendingSide'] == 'left':
							if teampos == 'away':
								fotype='L'
							else:
								fotype='R'
						else:
							if teampos == 'away':
								fotype='R'
							else:
								fotype='L'

				if fotype is not None:
					if fotaker not in lineinfo['faceoffs'][fotype]:
						lineinfo['faceoffs'][fotype][fotaker]=0
					lineinfo['faceoffs'][fotype][fotaker]=lineinfo['faceoffs'][fotype][fotaker]+1

				if fotaker not in lineinfo['faceoffs']['ALL']:
					lineinfo['faceoffs']['ALL'][fotaker]=0
				lineinfo['faceoffs']['ALL'][fotaker]=lineinfo['faceoffs']['ALL'][fotaker]+1
				game['lines'][abv]['line'][curshift['key']]=lineinfo

				foplayer=game['players'][str(fotaker)]

				maxfos=lineinfo['faceoffs']['ALL'][fotaker]
				maxplayer=fotaker
#				for p in lineinfo['positions'][foplayer['Position']]:
#					if p not in lineinfo['faceoffs']['ALL']:
#						continue
#
#					if lineinfo['faceoffs']['ALL'][p] > maxfos:
#						maxfos=lineinfo['faceoffs']['ALL'][p]
#						maxplayer=p

				game['lines'][abv]['line'][curshift['key']]=lineinfo

				if 'MakeC' not in lineinfo or lineinfo['MakeC'] != maxplayer:
					game['lines'][abv]['line'][curshift['key']]['MakeC']=maxplayer
					game=create_part_lines_from_scratch(game, abv, curshift['key'])

		for teampos in game['teams']:
			abv=game['teams'][teampos]['abv']
			shifti=game['lines'][abv]['last']['line']
			if shifti == -1:
				game['plays'][playi][abv]['line']=""
			else:
				shift=game['lines']['shifts']['line'][shifti]
				game['plays'][playi][abv]['line']=shift['key']

	for teampos in game['teams']:
		abv=game['teams'][teampos]['abv']
		game=end_line(game, len(game['plays'])-1, abv)
		for part in ['fline', 'dline', 'goalie']:
			game=end_part_line(game, abv, part, game['lines'][abv]['last']['line'])

	return game

def main():
	for i in range(1, len(sys.argv)):
		gamepk=sys.argv[i]
		season=None
		type=None
		gamenum=None
		if re.match('[0-9]+[/][0-9]+[/][0-9]+', gamepk):
			season=re.sub('[/].*$', '', gamepk)
			type=re.sub('^[^/]*[/]', '', gamepk)
			type=re.sub('[/].*$', '', type)
			gamenum=re.sub('^.*[/]', '', gamepk)
			gamepk = season[0:4]
			gamepk = gamepk + type
			gamepk = gamepk + gamenum
		else:
			print("Unrecognized argument: "+sys.argv[i])
			continue

		game = read_game(season, type, gamenum)
		if game is None:
			print("No data")
			continue

		if 'lines' in game:
			del(game['lines'])
#			print("Already processed")
#			continue

		game = add_lines(game)
		write_game(game)

main()
