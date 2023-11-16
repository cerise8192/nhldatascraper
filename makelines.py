#!/usr/bin/python3

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

def read_game(season, season_type, gamenum):
	game=None
	gamepath=get_game_path(season, season_type, gamenum)
	try:
		f=open(gamepath)
		game=f.readlines()
		f.close()
	except Exception as e:
		print(e)
		exit(1)
	
	game=''.join(game)
	game=json.loads(game)
	return game

def makelineinfo(game, linekey):
	lineinfo={}
	lineinfo['key']=linekey
	lineinfo['shifts']=[]
	lineinfo['toi']=0
	lineinfo['positions']=make_positions(game, linekey)
	game['lines']['line'][linekey]=lineinfo
	return game

def end_line(game, oldshifti, newshifti, playi):
	play = game['plays'][playi]
	oldshift = game['lines']['shifts'][oldshifti]
	oldshift['end']=playi
	oldshift['enddt']=play['dt']
	oldshift['toi']=oldshift['enddt']-oldshift['startdt']
	if newshifti is not None:
		shift['next']=oldshifti
	game['lines']['shifts'][oldshifti]=oldshift

	key=oldshift['key']
	game['lines']['line'][key]['toi']=game['lines']['line'][key]['toi']+oldshift['toi']

	return game

def make_positions(game, linekey):
	positions={}

	unknownd=[]
	unknownf=[]
	for nhlid in players:
		player=game['players'][nhlid]
		pos=player['Position']

		if pos == 'F':
			if 'Hand' in player:
				pos=player['Hand']+'W'
			else:
				unknownf.append(nhlid)
		elif pos == 'D':
			if 'Hand' in player:
				pos=player['Hand']+'D'
			else:
				unknownd.append(nhlid)

		if pos not in positions:
			positions[pos]=[nhlid]
		else:
			positions[pos].append(nhlid)

	for nhlid in unknownf:
		if 'C' not in positions:
			positions['C']=[]
		positions['C'].append(nhlid)
	
	for nhlid in unknownd:
		if 'RD' not in positions:
			positions['RD']=[nhlid]
		elif 'LD' not in positions:
			positions['LD']=[nhlid]
		else:
			positions['RD'].append(nhlid)

	return positions

def start_line(game, oldshifti, newshifti, playi, linekey):
	play=game['plays'][playi]

	shift={}
	shift['start']=playi
	shift['startdt']=play['dt']
	shift['key']=linekey
	if oldshifti is not None:
		shift['last']=oldshifti
	game['lines']['shifts'].insert(newshifti, shift)

	game['lines']['line'][linekey]['shifts'].append(newshifti)
	return game

def add_lines(game):
	if 'lines' not in game:
		game['lines']={}
		game['lines']['last']={}
		game['lines']['line']={}
		game['lines']['shifts']=[]

	for playi in range(0, len(game['plays'])):
		play=game['plays'][playi]
		if play['PLEvent'] == 'CHANGE':
			team=play['Team']
			linera=sorted(keys(play[team]['onice']))
			linekey=','.join(linera)
			if linekey not in game['lines']['line']:
				game=makelineinfo(game, linekey)
			oldshifti=None
			if team in game['lines']['last']:
				oldshifti=game['lines']['last'][team]
			newshifti=len(game['lines']['shifts'])
			game=end_line(game, oldshifti, newshifti, playi)
			game=start_line(game, oldshifti, newshifti, playi, linekey)
			print("Setting lastline for "+team)
			game['lines']['last'][team]=newshifti
			exit(5)

		elif play['PLEvent'] == 'FAC':
			for teampos in game['teams']:
				fotaker=None
				fotype=None

				abv=game['teams'][teampos]['abv']
				if abv not in game['lines']['last']:
					#print(json.dumps(play, indent=3))
					#print("No faceoff data for "+abv)
					continue

				curshifti=game['lines']['last'][abv]
				curshift=game['lines']['shifts'][curshifti]
				if 'faceoffs' not in curshift:
					curshift['faceoffs']={}
					curshift['faceoffs']['L']={}
					curshift['faceoffs']['R']={}
					curshift['faceoffs']['C']={}
					curshift['faceoffs']['ALL']={}
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
					if fotaker not in curshift['faceoffs'][fotype]:
						curshift['faceoffs'][fotype][fotaker]=0
					curshift['faceoffs'][fotype][fotaker]=curshift['faceoffs'][fotype][fotaker]+1

				if fotaker not in curshift['faceoffs']['ALL']:
					curshift['faceoffs']['ALL'][fotaker]=0
				curshift['faceoffs']['ALL'][fotaker]=curshift['faceoffs']['ALL'][fotaker]+1

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
		if 'lines' in game:
			del(game['lines'])
		game = add_lines(game)

main()
