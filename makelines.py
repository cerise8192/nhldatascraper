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
	except Exception as e:
		print(e)
		exit(1)
	
	game=''.join(game)
	game=json.loads(game)
	return game

def makelineinfo(game, team, linekey):
	debug=True
	if debug:
		print("   New line!  "+linekey)
	lineinfo={}
	lineinfo['key']=linekey
	lineinfo['team']=team
	lineinfo['shifts']=[]
	lineinfo['toi']=0
	game['lines'][team]['line'][linekey]=lineinfo
	game=make_positions(game, team, linekey)
	game=break_line(game, team, linekey)

	lineinfo=game['lines'][team]['line'][linekey]
	for part in ['fline', 'dline', 'goalie']:
		if lineinfo[part+'key'] not in game['lines'][team][part]:
			partlineinfo={}
			partlineinfo['strid']=lineinfo[part+'strid']
			partlineinfo['str']=lineinfo[part+'str']
			partlineinfo['key']=lineinfo[part+'key']
			partlineinfo['team']=team
			partlineinfo['shifts']=[]
			partlineinfo['toi']=0
			game['lines'][team][part][lineinfo[part+'key']]=partlineinfo
	return game

def end_line(game, oldshifti, newshifti, playi, team):
	debug=True
	if oldshifti is None:
		return game

	play = game['plays'][playi]
	oldshift = game['lines'][team]['shifts']['line'][oldshifti]
	if debug:
		print("   Ending shift #"+str(oldshifti)+" for "+oldshift['key']+" at play "+str(playi)+" dt "+str(play['dt']))

	oldshift['end']=playi
	oldshift['enddt']=play['dt']
	oldshift['toi']=oldshift['enddt']-oldshift['startdt']
	if newshifti is not None:
		oldshift['next']=newshifti
	game['lines'][team]['shifts']['line'][oldshifti]=oldshift

	key=oldshift['key']
	game['lines'][team]['line'][key]['toi']=game['lines'][team]['line'][key]['toi']+oldshift['toi']

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

def start_line(game, oldshifti, newshifti, playi, team, linekey):
	debug=True

	play=game['plays'][playi]
	if debug:
		print("   Starting shift #"+str(newshifti)+" for "+linekey+" at play "+str(playi)+" dt "+str(play['dt']))

	shift={}
	shift['start']=playi
	shift['startdt']=play['dt']
	shift['team']=team
	shift['key']=linekey
	if oldshifti is not None:
		shift['last']=oldshifti
	game['lines'][team]['shifts']['line'].insert(newshifti, shift)
	game['lines'][team]['line'][linekey]['shifts'].append(newshifti)

	return game

def get_name(game, nhlid):
	player=game['players'][nhlid]
	return player['Name']

def get_line_str(game, linekey):
	for team in game['lines']:
		if linekey not in game['lines'][team]['line']:
			continue
		game=break_line(game, linekey)
		return game['lines'][team]['line'][linekey]['linestr']
	return ""

def break_line(game, team, linekey):
	lineinfo=game['lines'][team]['line'][linekey]
	positions=lineinfo['positions']

	if 'pretty' in lineinfo:
		if 'MakeC' in lineinfo and len(lineinfo['positions']['C']) > 0 and lineinfo['positions']['C'][0] == lineinfo['MakeC']:
			return game
		del(lineinfo['pretty'])

	if 'MakeC' in lineinfo:
		if len(positions['C']) == 0:
			for pos in positions:
				if pos == 'C':
					continue
				for playeri in range(0, len(positions[pos])):
					if positions[pos][playeri] == lineinfo['MakeC']:
						positions[pos].pop(playeri)
						positions['C'].insert(0, lineinfo['MakeC'])
						print("   "+get_name(game, lineinfo['MakeC'])+" -> C by empty MakeC")
						break

		elif positions['C'][0] != lineinfo['MakeC']:
			oldnhlid=positions['C'][0]
			oldpos=game['players'][oldnhlid]['Position']
			positions['C'].pop(0)
			positions[oldpos].append(oldnhlid)

			for pos in positions:
				for playeri in range(0, len(positions[pos])):
					if positions[pos][playeri] == lineinfo['MakeC']:
						positions[pos].pop(playeri)
						positions['C'].insert(0, lineinfo['MakeC'])
						print("   "+get_name(game, lineinfo['MakeC'])+" -> C by MakeC")
						break

	deficit={}
	surplus={}
	for pos in positions:
		if len(positions[pos]) == 1:
			continue
		elif len(positions[pos]) == 0:
			deficit[pos]=0
		else:
			surplus[pos]=len(positions[pos])
	
	for have in list(surplus):
		n=len(positions[have])
		if n == 1:
			continue

		for playeri in range(len(positions[have])-1, -1, -1):
			nhlid=positions[have][playeri]
			player=game['players'][nhlid]
			if 'Hand' not in player:
				continue

			if have == 'LD' or have == 'RD' or have == 'D':
				if 'LD' in deficit and player['Hand'] == 'L':
					print("   "+get_name(game, nhlid)+" -> LD by hand & D")
					positions['LD'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['LD'])
					n=n-1
					break
				elif 'RD' in deficit and player['Hand'] == 'R':
					print("   "+get_name(game, nhlid)+" -> RD by hand & D")
					positions['RD'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['RD'])
					n=n-1
					break
			elif have != 'G':
				if 'LW' in deficit and player['Hand'] == 'L':
					print("   "+get_name(game, nhlid)+" -> LW by hand & F")
					positions['LW'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['LW'])
					n=n-1
					break
				elif 'RW' in deficit and player['Hand'] == 'R':
					print("   "+get_name(game, nhlid)+" -> RW by hand & F")
					positions['RW'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['RW'])
					n=n-1
					break

	for have in list(surplus):
		n=len(positions[have])
		for playeri in range(len(positions[have])-1, -1, -1):
			if n == 1:
				break

			nhlid=positions[have][playeri]
			if have == 'LD' or have == 'RD' or have == 'D':
				if 'LD' in deficit:
					print("   "+get_name(game, nhlid)+" -> LD by D")
					positions['LD'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['LD'])
					n=n-1
					break
				elif 'RD' in deficit:
					print("   "+get_name(game, nhlid)+" -> RD by D")
					positions['RD'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['RD'])
					n=n-1
					break
			elif have != 'G':
				if 'LW' in deficit:
					print("   "+get_name(game, nhlid)+" -> LW by F")
					positions['LW'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['LW'])
					n=n-1
					break
				elif 'RW' in deficit:
					print("   "+get_name(game, nhlid)+" -> RW by F")
					positions['RW'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['RW'])
					n=n-1
					break
				elif 'C' in deficit:
					print("   "+get_name(game, nhlid)+" -> C by F")
					positions['C'].append(nhlid)
					positions[have].pop(playeri)
					del(deficit['C'])
					n=n-1
					break

	for have in list(surplus):
		n=len(positions[have])
		if n == 1:
			continue

		for playeri in range(len(positions[have])-1, -1, -1):
			nhlid=positions[have][playeri]
			player=game['players'][nhlid]
			if 'Hand' not in player:
				continue

			possible=[]
			if player['Hand'] == 'L':
				possible=['LW', 'LD']
			elif player['Hand'] == 'R':
				possible=['RW', 'RD']

			for pos in possible:
				if pos not in deficit:
					continue
				print("   "+get_name(game, nhlid)+" -> "+pos+" by Hand")
				positions[pos].append(nhlid)
				positions[have].pop(playeri)
				del(deficit[pos])
				n=n-1
				break

	for have in list(surplus):
		n=len(positions[have])
		if n <= 1:
			continue

		for playeri in range(len(positions[have])-1, -1, -1):
			nhlid=positions[have][playeri]
			player=game['players'][nhlid]

			for pos in list(positions):
				if pos not in deficit or len(positions) >= 1:
					continue
				print("   "+get_name(game, nhlid)+" -> "+pos+" by Need")
				positions[pos].append(nhlid)
				positions[have].pop(playeri)
				del(deficit[pos])
				n=n-1
				break

	lineinfo['balanced']=positions
	
	fline=[]
	dline=[]
	goal=[]
	line=[]

	n=-1
	for pos in ['LW', 'C', 'RW']:
		n=n+1
		if len(positions[pos]) == 0:
			continue
		fline.insert(n, positions[pos][0])
		line.insert(n, fline[-1])

	n=-1
	for pos in ['LD', 'RD']:
		n=n+1
		if len(positions[pos]) == 0:
			continue
		dline.insert(n, positions[pos][0])
		line.insert(n+3, dline[-1])

	n=-1
	for pos in ['G']:
		n=n+1
		if len(positions[pos]) == 0:
			continue
		goal.insert(n, positions[pos][0])
		line.insert(n+5, goal[-1])

	for pos in positions:
		for i in range(1, len(positions[pos])):
			if pos == 'G':
				goal.append(positions[pos][i])
			elif pos == 'LD' or pos == 'RD':
				dline.append(positions[pos][i])
			else:
				fline.append(positions[pos][i])
			line.append(positions[pos][i])
	
	lineinfo['linestrid']=','.join(line)
	lineinfo['flinestrid']=','.join(fline)
	lineinfo['dlinestrid']=','.join(dline)
	lineinfo['goaliestrid']=','.join(goal)

	lineinfo['flinekey']=','.join(sorted(fline))
	lineinfo['dlinekey']=','.join(sorted(dline))
	lineinfo['goaliekey']=','.join(sorted(goal))

	for i in range(0, len(fline)):
		f=fline[i]
		f=get_name(game, f)
		f=re.sub('^[^#]*[#]', '#', f)
		f=re.sub('[ ][^ ]*[ ]', ' ', f)
		fline[i]=f
	lineinfo['flinestr']=lineinfo['team']+' '+' '.join(fline)

	for i in range(0, len(dline)):
		d=dline[i]
		d=get_name(game, d)
		d=re.sub('^[^#]*[#]', '#', d)
		d=re.sub('[ ][^ ]*[ ]', ' ', d)
		dline[i]=d
	lineinfo['dlinestr']=lineinfo['team']+' '+' '.join(dline)

	for i in range(0, len(goal)):
		g=goal[i]
		g=get_name(game, g)
		g=re.sub('^[^#]*[#]', '#', g)
		g=re.sub('[ ][^ ]*[ ]', ' ', g)
		goal[i]=g
	lineinfo['goaliestr']=lineinfo['team']+' '+' '.join(goal)

	for i in range(0, len(line)):
		l=line[i]
		l=get_name(game, l)
		l=re.sub('^[^#]*[#]', '#', l)
		l=re.sub('[ ][^ ]*[ ]', ' ', l)
		line[i]=l
	lineinfo['linestr']=lineinfo['team']+' '+' '.join(line)
	lineinfo['pretty']=True

	print("      L: "+lineinfo['linestr'])
	print("         F: "+lineinfo['flinestr'])
	print("         D: "+lineinfo['dlinestr'])
	print("         G: "+lineinfo['goaliestr'])
	game['lines'][team]['line'][linekey]=lineinfo

	return game

def part_line(game, oldshifti, newshifti, playi):
	newinfo=game['lines'][team]['line'][linekey]
		
	for part in ['fline', 'dline', 'goalie']:
		if oldshifti is not None:
			oldshift=game['lines'][team]['shifts']['line'][oldshifti]
			oldinfo=game['lines'][team]['line'][oldshift['key']]
			if oldinfo[part+'key'] == newinfo[part+'key']:
				continue
			oldshift=game['lines'][team]['shifts'][part][oldshifti]

	#lineinfo['flinestrid']
	#lineinfo['dlinestrid']
	#lineinfo['goaliestrid']
	#lineinfo['flinekey']
	#lineinfo['dlinekey']
	#lineinfo['goaliekey']
	#lineinfo['flinestr']
	#lineinfo['dlinestr']
	#lineinfo['goaliestr']




def add_lines(game):
	debug=True
	if 'lines' not in game:
		game['lines']={}
		for teampos in game['teams']:
			abv=game['teams'][teampos]['abv']
			game['lines'][abv]={}
			game['lines'][abv]['last']={}
			game['lines'][abv]['shifts']={}
			for part in ['line', 'fline', 'dline', 'goalie']:
				game['lines'][abv]['last'][part]=-1
				game['lines'][abv][part]={}
				game['lines'][abv]['shifts'][part]=[]

	for playi in range(0, len(game['plays'])):
		play=game['plays'][playi]
		if debug:
			print(str(play['dt'])+" - "+play['PLEvent'])

		if play['PLEvent'] == 'CHANGE':
			team=play['Team']
			linera=sorted(list(play[team]['onice']))
			linekey=','.join(linera)
			if linekey not in game['lines'][team]['line']:
				game=makelineinfo(game, team, linekey)

			oldshifti=None
			if game['lines'][team]['last']['line'] != -1:
				oldshifti=game['lines'][team]['last']['line']
			newshifti=len(game['lines'][team]['shifts']['line'])
			game=end_line(game, oldshifti, newshifti, playi, team)
			game=start_line(game, oldshifti, newshifti, playi, team, linekey)
			game['lines'][team]['last']['line']=newshifti

			for part in ['fline', 'dline', 'goalie']:
				newlineshift=game['lines'][team]['shifts']['line'][newshifti]
				newlinekey=newlineshift['key']
				newlineinfo=game['lines'][team]['line'][newlinekey]
				if game['lines'][team]['last'][part] != -1:
					oldlineshift=game['lines'][team]['shifts']['line'][oldshifti]
					oldlinekey=oldlineshift['key']
					oldlineinfo=game['lines'][team]['line'][oldlinekey]

					if oldlineinfo[part+'key'] == newlineinfo[part+'key']:
						continue

					oldpartshifti=game['lines'][team]['last'][part]
					oldpartshift=game['lines'][team]['shifts'][part][oldpartshifti]

					oldpartshift['enddt']=play['dt']
					oldpartshift['end']=playi
					oldpartshift['toi']=oldpartshift['enddt']-oldpartshift['startdt']
					game['lines'][team]['shifts'][part][oldpartshifti]=oldpartshift

					oldpartinfo=game['lines'][team][part][oldpartshift['key']]
					oldpartinfo['toi']=oldpartinfo['toi']+oldpartshift['toi']
					game['lines'][team][part][oldpartshift['key']]=oldpartinfo

				newpartshift={}
				newpartshift['team']=newlineinfo['team']
				newpartshift['key']=newlineinfo[part+'key']
				newpartshift['startdt']=play['dt']
				newpartshift['start']=playi
				newpartshift['toi']=0
				newpartshifti=len(game['lines'][team]['shifts'][part])
				game['lines'][team]['shifts'][part].insert(newpartshifti, newpartshift)
				game['lines'][team]['last'][part]=newpartshifti
				game['lines'][team][part][newpartshift['key']]['shifts'].append(newpartshifti)

		elif play['PLEvent'] == 'FAC':
			for teampos in game['teams']:
				fotaker=None
				fotype=None

				abv=game['teams'][teampos]['abv']
				if game['lines'][team]['last']['line'] != -1:
					continue

				curshifti=game['lines'][team]['last']['line'][abv]
				curshift=game['lines'][team]['shifts']['line'][curshifti]
				lineinfo=game['lines'][team]['line'][curshift['key']]
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
				game['lines'][team]['line'][curshift['key']]=lineinfo

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

				game['lines'][team]['line'][curshift['key']]=lineinfo

				if 'MakeC' not in lineinfo or lineinfo['MakeC'] != maxplayer:
					game['lines'][team]['line'][curshift['key']]['MakeC']=maxplayer
					game=break_line(game, team, linekey)

		for abv in game['lines']:
			shifti=game['lines'][abv]['last']['line']
			if shifti == -1:
				game['plays'][playi][abv]['line']=""
			else:
				shift=game['lines'][abv]['shifts']['line'][shifti]
				game['plays'][playi][abv]['line']=shift['key']


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
			continue

		game = add_lines(game)
		write_game(game)

main()
