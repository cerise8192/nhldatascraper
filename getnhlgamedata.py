#!/usr/bin/python3

import os
import sys
import datetime
import requests
import json
import time
import re
import math
import concurrent.futures
import bz2
from unidecode import unidecode
from bs4 import BeautifulSoup,NavigableString,Tag
from websockets.sync.client import connect

def penalty_type(text):
	types=['Abuse of officials', 'Abusive language', 'Aggressor', 'Bench', 'Boarding', 'Broken stick', 'Butt ending', 'Charging', 'Clipping', 'Closing hand on puck', 'Coach/Mgr on ice - bench', 'Covering puck in crease', 'Cross checking', 'Cross-checking', 'Delay Game', 'Delay Game - Bench - FO Viol', 'Delay Game - Bench - FO viol', 'Delay Game - Equipment', 'Delay Game - FO Viol - hand', 'Delay Game - Goalie - restrict', 'Delay Game - Puck over glass', 'Delay Game - Smothering puck', 'Delay Game - Unsucc chlg', 'Delay Game - Unsucc chlg', 'Elbowing', 'Embellishment', 'Fighting', 'Game Misconduct', 'Game Misconduct - Head coach', "Goalie participat'n byd Center", 'Goalkeeper displaced net', 'Goalie leave crease', 'Hi stick', 'Hi-sticking', 'High-sticking', 'Holding', 'Holding stick', 'Holding the stick', 'Hooking', 'Illegal check to head', 'Illegal stick', 'Instigator', 'Interference', 'Interference on goalkeeper', 'Kneeing', 'Match [Pp]enalty', 'Minor', 'Misconduct', "Playing without a helmet", "Puck thrown fwd - Goalkeeper", "Removing opponent's helmet", 'Roughing', 'Roughing - Removing opp helmet', 'Slash', 'Slashing', 'Spearing', 'Throwing equipment', 'Throwing stick', 'Throw object at puck', 'Too many men/ice', 'Tripping', 'Unsportsmanlike conduct']
	for penaltytype in types:
		penalty_match=re.search('[ \t\n\r\f\v]*'+penaltytype+'[ \t\n\r\f\v]*', text)
		if penalty_match is not None:
			start=penalty_match.start()
			end=penalty_match.end()
			if start > 2 and text[start-2:start] == 'PS-':
				start=start-2
			print('Start: '+text[start-2:start])

			textend=len(text)
			print('End  : '+text[end:end+5])
			print('End2 : '+text[end:end+14])
			print('End3 : '+text[end:end+12])
			if end < textend-5 and text[end:end+5] == ' - dbl':
				end=end+5
			elif end < textend-14 and text[end:end+14] == ' - double minor':
				end=end+14
			elif end < textend-12 and text[end:end+12] == ' on breakaway':
				end=end+12
			return text[start:end]
	return None

def shot_type(text):
	types=['Backhand', 'Bat', 'Between Legs', 'Cradle', 'Deflected', 'Failed Attempt', 'Poke', 'Slap', 'Snap', 'Tip-In', 'Wrap-around', 'Wrist']
	for shottype in types:
		if re.search('[ \t\n\r\f\v]*'+shottype+'[ \t\n\r\f\v]*', text):
			return shottype
	return None

def miss_type(text):
	types=[ 'Above Crossbar', 'Goalpost', 'High and Wide Left', 'High and Wide Right', 'Hit Crossbar', 'Hit Left Post', 'Hit Right Post', 'Over Net', 'Short', 'Wide Left', 'Wide of Net', 'Wide Right']
	for misstype in types:
		if re.search('[ \t\n\r\f\v]*'+misstype+'[ \t\n\r\f\v]*', text):
			return misstype
	return None

def zone_type(text):
	types=['Off. Zone', 'Neu. Zone', 'Def. Zone']
	for zonetype in types:
		if re.search('[ \t\n\r\f\v]*'+zonetype+'[ \t\n\r\f\v]*', text):
			return zonetype
	return None

def cachename(url):
	cachename=re.sub('^[^:]*[:][/][/]', '', url)
	cachename=re.sub('['+os.sep+']', '_', cachename)
	cachename='cache/'+cachename
	return cachename

def wget(url):
	cachefile=cachename(url)
	text=None

	try:
		f=bz2.open(cachefile, "r")
		text=''
		for line in f.readlines():
			text=text+line.decode("utf-8")
		#text=''.join(f.readlines().decode("utf-8"))
		f.close()
	except Exception as e:
		text=None
		pass

	if text is None:
		try:
			f=open(cachefile, 'r')
			text=''.join(f.readlines())
			f.close()
		except Exception as e:
			text=None
			pass

	if text is None:
		headers={}
		headers['Referer']='https://www.nhl.com'
		headers['Origin']='https://www.nhl.com'
		session=requests.Session()
		try:
			response=session.get(url, headers=headers)
			if response.status_code == 200:
				text=response.text
				os.makedirs("cache", exist_ok=True)
#				f=open(cachefile, 'x')
#				f.write(text)
#				f.close()
				f=bz2.open(cachefile, 'x')
				f.write(bytes(text, 'utf-8'))
				f.close()
				
			else:
				print("code = "+str(response.status_code))
		except Exception as e:
			print("Could not retrieve "+url+": "+str(e))
			pass

	return text

def get_name_combos(startname):
	names=[]

	names.append(startname)
	newnames=[]
	for name in names:
		newnames.append(name)
		if unidecode(name) != name:
			newnames.append(unidecode(name))
	names=newnames
	newnames=[]

	for name in names:
		newnames.append(name)
		if name != name.upper():
			newnames.append(name.upper())
	names=newnames
	newnames=[]

	for name in names:
		newnames.append(name)
		if re.search('#', name):
			newnames.append(re.sub('#', '', name))
	names=newnames
	newnames=[]
	
	for name in names:
		ra=re.split('[- \t\n\r\f\v]', name)
		matches=re.findall('[- \t\n\r\f\v]', name)

		for i in range(1, 2**(len(ra))):
			n=[]
			for j in range(0, len(ra)):
				if i & (2**j) > 0:
					n.insert(j, True)
				else:
					n.insert(j, False)

			newname=""
			for j in range(0, len(ra)):
				if n[j]:
					if j > 0 and n[j-1]:
						newname=newname+matches[j-1]+ra[j]
					elif len(newname) == 0:
						newname=ra[j]
					else:
						newname=newname+' '+ra[j]
			newnames.append(newname)
	names=sorted(newnames, key=len, reverse=True)

	return names

def debug_html(tag, indent=0, path=''):
	if tag is None:
		return
	indent_str=''
	for i in range(0, indent):
		indent_str=indent_str+'   '

	if path != '':
		path=path+'->'
	path=path+str(tag.name)

	if str(tag.name) != 'None':
		print("path:"+indent_str+path)
		printme=indent_str+'<'+str(tag.name)
		for attr in tag.attrs:
			try:
				printme=printme+' '+str(attr)+'='+str(tag[attr])
			except TypeError as e:
				pass
		printme=printme+'>'
		if tag.string is not None and len(tag.string) > 0:
			if tag.name != 'style' and tag.name != 'script':
				printme=printme+' '+tag.string
		elif tag.text is not None and len(tag.text) > 0:
			printme=printme+' '+tag.text
		print(printme)

	try:
		i=0
		for child in tag.children:
			debug_html(child, indent+1, path+'['+str(i)+']')
			i=i+1
	except AttributeError as e:
		pass

def debug_dict(dict, indent, path=''):
	indent_str=''
	for i in range(0, indent):
		indent_str=indent_str+'   '
	for k in dict:
		print(indent_str+str(k))
		print(indent_str+path+'->'+str(k))
		debug(dict[k], indent+1, path+'->'+str(k))

def debug_array(dict, indent, path=''):
	indent_str=''
	for i in range(0, indent):
		indent_str=indent_str+'   '
	for k in range(0, len(dict)):
		print(indent_str+str(k))
		print(indent_str+path+'->'+str(k))
		debug(dict[k], indent+1, path+'->'+str(k))

def debug_str(dict, indent, path=''):
	indent_str=''
	for i in range(0, indent):
		indent_str=indent_str+'   '
	print(indent_str+dict)

def debug(dict, indent=0, path=''):
	if type(dict) == type({}):
		debug_dict(dict, indent, path)
	elif type(dict) == type([]):
		debug_array(dict, indent, path)
	elif type(dict) == type(''):
		debug_str(dict, indent, path)
	elif type(dict) == type(0):
		debug_str(str(dict), indent, path)
	elif type(dict) == type(0.0):
		debug_str(str(dict), indent, path)
	elif type(dict) == type(True):
		debug_str(str(dict), indent, path)
	else:
		print("Unknown type: "+str(type(dict)))

def get_text_alone(tag):
	return tag.text
	
def get_string(tag):
	str=get_string_recurse(tag)
	if re.search('^[ \t\n\r\f\v]*$', str) is not None:
		str=get_alt_string(tag)

#	if tag is not None and re.search('Time', str):
#		decode=tag.decode_contents()
#		text=tag.get_text()
#		if str != decode or str != text or decode != text:
#			print("Would return: "+str)
#			print("Might return: "+decode)
#			print("Or maybe: "+text)
#			exit(7)
	return str

def get_string_recurse(tag):
	retstr=""
	if isinstance(tag, Tag):
		for child in tag.children:
			retstr=retstr+get_string_recurse(child)

		if tag.string is not None:
			retstr=retstr+tag.string
		elif tag.text is not None:
			retstr=retstr+tag.text

	return retstr
	

def get_alt_string(tag):
	str=""
	if tag is not None and isinstance(tag, Tag):
		for child in tag.children:
			str=str+get_alt_string(child)

		if tag.name == 'img':
			if 'title' in tag.attrs:
				newstr=tag.attrs['title']
			elif  'alt' in tag.attrs:
				newstr=tag.attrs['alt']

			newstr=newstr.replace('\n', '').rstrip()
			str=str+newstr
	return str

def nav_tag(root, path):
	if root is None or len(path) == 0:
		return root
	i=0
	n=path.pop(0)
	passpath=[]
	for step in path:
		passpath.append(step)
	if not isinstance(root, NavigableString) and root is not None:
		if isinstance(n, int):
			for child in root.children:
				if i == n:
					return nav_tag(child, passpath)
				i=i+1
		elif isinstance(n, str):
			for child in root.children:
				if child.name == n:
					return nav_tag(child, passpath)
	return None

def tag_search(root, namepath):
	tags=[]
	if isinstance(root, NavigableString) or root is None:
		pass
	elif len(namepath) == 0:
		tags.append(root)
	else:
		nextname=namepath.pop(0)
		for child in root.children:
			if isinstance(child, NavigableString) or child is None:
				continue
			if child.name != nextname:
				continue

			passpath=[]
			for name in namepath:
				passpath.append(name)

			foundtags=tag_search(child, passpath)
			for tag in foundtags:
				tags.append(tag)

	return tags

def get_schedule(start, end=None):
	text=wget('https://api-web.nhle.com/v1/score/'+start)
	if text is None:
		return None
	sched=json.loads(text)

	games=[]
	if 'games' in sched:
		for game in sched['games']:
			entry={}
			entry['away']=game['awayTeam']['abbrev']
			entry['home']=game['homeTeam']['abbrev']
			entry['gamePk']=game['id']
			entry['gameType']=game['gameType']
			entry['season']=game['season']
			entry['link']=game['gameCenterLink']
			if 'clock' in game:
				entry['clock']=game['clock']
			games.append(entry)
	return games

def get_live_schedule(start, end=None):
	if end is None:
		end=start

#https://statsapi.web.nhl.com/api/v1/schedule?startDate=2021-02-20&endDate=2021-02-20&hydrate=team,linescore,broadcasts(all),tickets,game(content(media(epg)),seriesSummary),radioBroadcasts,metadata,seriesSummary(series)&site=en_nhl&teamId=&gameType=&timecode=
	text=wget('https://statsapi.web.nhl.com/api/v1/schedule?startDate='+start+'&endDate='+end)
	if text is None:
		return None
	sched=json.loads(text)

	games=[]
	try:
		for date in sched['dates']:
			try:
				for game in date['games']:
					id=game['gamePk'] #2020020274
					type=game['gameType'] #R == regular season, P == playoff, PR == preseason, A == All-Star Game
					season=game['season'] #20202021
					link=game['link'] #/api/v1/game/2020020274/feed/live
					games.append(game)
			except KeyError as e:
				pass
	except KeyError as e:
		pass
	return games

def get_livedata(game):
	url='https://statsapi.web.nhl.com/api/v1/game/'+str(game['gamePk'])+'/feed/live?site=en_nhl'
	text=wget(url)
	if text is None:
		return None
	try:
		livedata=json.loads(text)
	except Exception as e:
		print(text)
		print(url)
		print(e)
		exit(41)
	return livedata


def get_edge_card(nhlid):
	build={}
	build['type']='action'
	build['event']={}

	build['event']['domain']='edge.nhl.com'
	build['event']['uri']="/en/skater/"+str(nhlid)
	build['event']['action']='load'

	build['event']['data']={}
	build['event']['data']['callbackFunction']="initializeDataElements"
	build['event']['data']['renderFunction']="renderPlayerCard"
	build['event']['data']['target']="#profile-playercard"

	build['event']['data']['params']={}
	build['event']['data']['params']['player']=str(nhlid)
	build['event']['data']['params']['rootName']="skatersProfiles"
	build['event']['data']['params']['source']="players"
	build['event']['data']['params']['type']="skaters"

	return build

def get_edge_profile_player(nhlid):
	build={}
	build['type']='action'
	build['event']={}

	build['event']['domain']='edge.nhl.com'
	build['event']['uri']="/en/skater/"+str(nhlid)
	build['event']['action']='load'

	build['event']['data']={}
	build['event']['data']['callbackFunction']="initializeDataElements"
	build['event']['data']['renderFunction']="renderProfilePlayerSection"
	build['event']['data']['target']="#profile-section"

	build['event']['data']['params']={}
	build['event']['data']['params']['player']=str(nhlid)
	build['event']['data']['params']['rootName']="skatersProfiles"
	build['event']['data']['params']['source']="players"
	build['event']['data']['params']['type']="skaters"

	return build

def get_edge_profile(nhlid):
	build={}
	build['type']='action'
	build['event']={}

	build['event']['domain']='edge.nhl.com'
	build['event']['uri']="/en/skater/"+str(nhlid)
	build['event']['action']='load'

	build['event']['data']={}
	build['event']['data']['renderFunction']='renderProfileContent'
	build['event']['data']['callbackFunction']="runClientFns"
	build['event']['data']['target']="#zonetime-section-content"

	build['event']['data']['params']={}
	build['event']['data']['params']['feed']="skatersProfiles"
	build['event']['data']['params']['id']=str(nhlid)
	build['event']['data']['params']['manpower']="all"
	build['event']['data']['params']['season']="20232024"
	build['event']['data']['params']['sectionName']="zonetime"
	build['event']['data']['params']['stage']="regular"
	build['event']['data']['params']['units']="imperial"

	return build


def get_edge(nhlid):
	ws=connect("wss://edge.nhl.com/en/skater/"+str(nhlid))
	#getlabel='{"type":"action","event":{"domain":"edge.nhl.com","uri":"/en/skater/'+str(nhlid)+'","action":"getLabel","data":{"params":{"type":"skaters","player":"'+str(nhlid)+'","rootName":"skatersProfiles","source":"players"}}}}'
	for build in [get_edge_profile(nhlid), get_edge_profile_player(nhlid), get_edge_card(nhlid)]:
		ws.send(json.dumps(build))
	message=ws.recv()
	print(str(message))

#get_edge(8476881)
#exit(9)



def get_pxp(game):
	playbyplay={}
	for suffix in ['play-by-play', 'landing', 'boxscore']:
		url='https://api-web.nhle.com/v1/gamecenter/'+str(game['gamePk'])+'/'+suffix
		print("get_pxp for "+url)
		text=wget(url)
		if text is None:
			continue
		try:
			with open('/tmp/pxp-'+suffix, 'w') as f:
				f.write("wget\n")
				f.write(text)
				f.close()
			newdata=json.loads(text)
			for k in newdata:
				if k not in playbyplay:
					playbyplay[k]=newdata[k]
				with open('/tmp/pxp-'+suffix, 'w') as f:
					f.write("json\n")
					f.write(json.dumps(playbyplay[k], indent=3))
					f.close()
		except Exception as e:
			print(text)
			print(url)
			print(e)
			exit(41)

	url="https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId="+str(game['gamePk'])+"%20and%20((duration%20!=%20%2700:00%27%20and%20typeCode%20=%20517)%20or%20typeCode%20!=%20517%20)"
	text=wget(url)
	if text is None:
		return None
	try:
		with open('/tmp/pxp-shifts', 'w') as f:
			f.write("wget\n")
			f.write(text)
			f.close()
		newdata=json.loads(text)
		playbyplay['shifts']=newdata
		with open('/tmp/pxp-shifts', 'w') as f:
			f.write("json\n")
			f.write(json.dumps(playbyplay['shifts'], indent=3))
			f.close()
	except Exception as e:
		print(text)
		print(url)
		print(e)
		exit(41)

	return playbyplay

def get_game_info(data, collated):
	collated['GAME']=data['GAME']

	collated['gamePk']=str(data['GAME']['gamePk'])
	collated['year']=collated['gamePk'][0:4]
	collated['season']=str(int(collated['year']))+str(int(collated['year'])+1)
	collated['season_type']=collated['gamePk'][4:6]
	collated['game']=collated['gamePk'][6:]
	collated['date']=data['PXP']['gameDate']

	return collated

def get_gamedata(game):
	gameid=str(game['gamePk'])
	game['html']={}
	game['html']['y']=gameid[0:4]
	game['html']['t']=gameid[4:6]
	game['html']['n']=gameid[6:]

	data={}

	data['GAME']=game
	print("Game on "+data['GAME']['link'])

	print("apiweb Play by play..."+gameid)
	data['PXP']=get_pxp(game)

	print("statsweb livedata..."+gameid)
	data['LIVE']=get_livedata(game)

	print("Play by play..."+gameid)
	data['PL']=get_pl(game)
	data['PLNOTE']=[]
	if data['PL'] is not None:
		while len(data['PL']) > 0 and data['PL'][0]['Event'] == 'NOTE':
			data['PLNOTE'].append(data['PL'].pop(0))
	
	print("Rosters..."+gameid)
	data['RO']=get_ro(game)
	print("Visitor TOI..."+gameid)
	data['TV']=get_tv(game)
	print("Home TOI..."+gameid)
	data['TH']=get_th(game)
	keys=list(data)
	for k in keys:
		if data[k] is None:
			if k == 'LIVE':
				del(data[k])
			elif k == 'PXP':
				del(data[k])
			else:
				print(gameid+': '+k+' failed to parse')
				return None

	return data

def get_tv(game):
	url='http://www.nhl.com/scores/htmlreports/'+str(game['season'])+'/TV'+game['html']['t']+game['html']['n']+'.HTM'
	text=wget(url)
	if text is None:
		return None
	soup = BeautifulSoup(text, 'html.parser')
	return get_toi(soup)

def get_th(game):
	url='http://www.nhl.com/scores/htmlreports/'+str(game['season'])+'/TH'+game['html']['t']+game['html']['n']+'.HTM'
	text=wget(url)
	if text is None:
		return None
	soup = BeautifulSoup(text, 'html.parser')
	return get_toi(soup)

def get_toi(soup):
	debug=False
	toi={}
	roots=[[0, 5, 3, 1], [1, 5, 5, 1], [1, 1, 5, 5, 1], [0,5,1,1]]
	root=soup
	for rootra in roots:
		root=nav_tag(soup, rootra)
		team=get_string(nav_tag(root, [5, 1, 1, 1, 1]))
		if team != '':
			toi['Team']=team
			break
	if 'Team' not in toi:
		debug_html(soup)
		print("TOI parse didn't work")
		return None

	player=''
	cols=[]
	table_root=nav_tag(root, [7, 1, 1])
	for tr in tag_search(table_root, ['tr']):
		tds=tag_search(tr, ['td'])

		if len(tds) == 1:
			#This can be a blank space (class includes 'spacer')
			if 'class' in tds[0].attrs:
				skip=False
				for attr in tds[0].attrs['class']:
					if attr == 'spacer':
						skip=True
				if skip:
					continue

			#This can be the start of a summary table (tr->tds[0]->table)
			summary=tag_search(tr, ['td', 'table'])
			if len(summary) > 0:
				continue

			#This can be a player's name & number			
			player=get_string(tds[0])
			if re.search('^[ \t\n\r\f\v]*[0-9]+[ \t\n\r\f\v]+[^,]+[,][ \t\n\r\f\v]+.*', player):
				num=re.sub('^[ \t\n\r\f\v]+', '', player)
				num=re.sub('[ \t\n\r\f\v]+.*', '', num)

				last=re.sub('^[ \t\n\r\f\v]*[0-9]+[ \t\n\r\f\v]+', '', player)
				last=re.sub('[,].*$', '', last)

				first=re.sub('^.*[,][ \t\n\r\f\v]*', '', player)

				player=num+' '+first+' '+last
				if player not in toi:
					toi[player]=[]
				if debug:
					print('Player TOI: '+player)
				cols=[]
				continue

			#This can also be something I've never thought about
			debug_html(tr)
			print("Unknown single td")
			return None

		elif len(tds) == 6:
			vals=[]
			for td in tds:
				string=get_string(td)
				string=re.sub('^[ \t\n\r\f\v]*', '', string)
				string=re.sub('[ \t\n\r\f\v]*$', '', string)
				vals.append(string)

			if len(cols) == 0:
				cols=vals
				if cols[0] == 'Shift #' and cols[1] == 'Per' and cols[4] == 'Duration':
					cols[2]='Start of Shift'
					cols[3]='End of Shift'
					cols[5]='Event'
				#French
				elif cols[1] == 'Per':
					cols=['Shift #', 'Per', 'Start of Shift', 'End of Shift', 'Duration', 'Event']
				if debug:
					print('   Cols: '+','.join(cols))
			else:
				shift={}
				for i in range(0, len(vals)):
					if debug:
						print('   '+cols[i]+' = '+vals[i])
					shift[cols[i]]=vals[i]
				if re.match('^[ \t\n\r\f\v]*[0-9:]+[ \t\n\r\f\v]*[/][ \t\n\r\f\v]*[0-9:]+[ \t\n\r\f\v]*$', shift['Start of Shift']):
					shift['StartEL']=re.sub('[ \t\n\r\f\v]*[/].*$', '', shift['Start of Shift'])
					shift['StartEL']=re.sub('^[0]+([0-9]+)', '\\1', shift['StartEL'])

					shift['StartREM']=re.sub('^.*[/][ \t\n\r\f\v]*', '', shift['Start of Shift'])
					shift['StartREM']=re.sub('^[0]+([0-9]+)', '\\1', shift['StartREM'])
				if re.match('^[ \t\n\r\f\v]*[0-9:]+[ \t\n\r\f\v]*[/][ \t\n\r\f\v]*[0-9:]+[ \t\n\r\f\v]*$', shift['End of Shift']):
					shift['EndEL']=re.sub('[ \t\n\r\f\v]*[/].*$', '', shift['End of Shift'])
					shift['EndEL']=re.sub('^[0]+([0-9]+)', '\\1', shift['EndEL'])

					shift['EndREM']=re.sub('^.*[/][ \t\n\r\f\v]*', '', shift['End of Shift'])
					shift['EndREM']=re.sub('^[0]+([0-9]+)', '\\1', shift['EndREM'])
				if shift['Per'] == 'OT':
					shift['Per']=4
				toi[player].append(shift)

		else:
			debug_html(tr)
			print("Unknown number of tds")
			return None
				
	return toi

def get_pl(game):
	pl=get_pl_2019(game)
#	if len(pl) == 0:
#		pl=get_pl_2018(game)

	return pl


def get_pl_2018(game):
	debug_pl=False
	url='http://www.nhl.com/scores/htmlreports/'+str(game['season'])+'/PL'+game['html']['t']+game['html']['n']+'.HTM'
	if (debug_pl):
		print(url)
	text=wget(url)
	if text is None:
		return None
	soup = BeautifulSoup(text, 'html.parser')
	pl=[]

	root=nav_tag(soup, [0, 5])
	#soup = document, 0 = html, 5 = body

	gameinfo=nav_tag(soup, [0, 5, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1])
	debug_html(gameinfo)
	print('---')
	for tag in tag_search(gameinfo, ['table', 'tr', 'td']):
		print(get_string(tag))
	exit(5)


	gameinfo=nav_tag(soup, [0, 5, 3, 1, 1, 1, 1, 1])
	for td in tag_search(gameinfo, ['tr', 'td']):
		text=get_string(td)
		event={}
		event['Event']='NOTE'
		event['Description']=text
		event['Per']="1"
		event['Elapsed']="0:00"
		event['Remaining']="20:00"
		event['#']="0"
		pl.append(event)

	cols=[]
	for table in tag_search(root, ['div', 'table']):
		for tr in tag_search(table, ['tr']):
			if debug_pl:
				debug_html(tr)
			tds=tag_search(tr, ['td'])

			if len(tds) == 1:
				cols=[]
				continue

			if len(cols) == 0:
				vals=[]
				for td in tds:
					vals.append(get_string(td))
					if vals[-1] == '':
						vals[-1]='Time'

				cols=vals
				if (debug_pl):
					print(",".join(cols))
			else:
				event={}
				for i in range(0, len(cols)):
					td=tds[i]

					if re.search('[ \t\n\r\f\v]+On[ \t\n\r\f\v]+Ice[ \t\n\r\f\v]*$', cols[i]):
						team=re.sub('[ \t\n\r\f\v]+On[ \t\n\r\f\v]+Ice[ \t\n\r\f\v]*$', '', cols[i])
						line=[]
						for playertag in tag_search(td, ['table', 'tr', 'td', 'table', 'tr', 'td', 'font']):
							number=get_string(playertag)
							position=re.sub('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*.*$', '', playertag.attrs['title'])
							player=re.sub('^.*[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*', '', playertag.attrs['title'])
							line.append(team+' #'+number+' '+player)
							if (debug_pl):
								print("   Player: "+str(len(line))+" = "+line[-1])
						event[cols[i]]=','.join(line)
					elif re.search('Time:ElapsedGame', cols[i]):
						event[cols[i]]=get_string(td)
						timesplit=event[cols[i]].split(':')
						event['Elapsed']=timesplit[0]+':'+timesplit[1][0:2]
						event['Remaining']=timesplit[1][2:]+':'+timesplit[2]
						if (debug_pl):
							print("   Elapsed="+event['Elapsed'])
							print("   Remaining="+event['Remaining'])
					else:
						event[cols[i]]=get_string(td)

					if (debug_pl):
						print("   "+str(i)+" -> "+cols[i]+" = "+event[cols[i]])

				if (debug_pl):
					debug(event)

				pl.append(event)
	return pl

def get_pl_2019(game):
	debug_pl=False
	url='http://www.nhl.com/scores/htmlreports/'+str(game['season'])+'/PL'+game['html']['t']+game['html']['n']+'.HTM'
	if (debug_pl):
		print(url)
	text=wget(url)
	if text is None:
		return None
	soup = BeautifulSoup(text, 'html.parser')
	pl=[]

	root=nav_tag(soup, [0, 5])
	#soup = document, 0 = html, 5 = body


	gameinfo=nav_tag(soup, [0, 5, 3, 1, 1, 1, 1, 1])
	for td in tag_search(gameinfo, ['tr', 'td']):
		text=get_string(td)
		event={}
		event['Event']='NOTE'
		event['Description']=text
		event['Per']="1"
		event['Elapsed']="0:00"
		event['Remaining']="20:00"
		event['#']="0"
		pl.append(event)

	cols=[]
	for table in tag_search(root, ['div', 'table']):
		for tr in tag_search(table, ['tr']):
			if debug_pl:
				debug_html(tr)
			tds=tag_search(tr, ['td'])

			if len(tds) == 1:
				cols=[]
				continue

			if len(cols) == 0:
				vals=[]
				for td in tds:
					vals.append(get_string(td))
					if vals[-1] == '':
						vals[-1]='Time'

				cols=vals
				if (debug_pl):
					print(",".join(cols))
			else:
				event={}
				for i in range(0, len(cols)):
					td=tds[i]

					if re.search('[ \t\n\r\f\v]+On[ \t\n\r\f\v]+Ice[ \t\n\r\f\v]*$', cols[i]):
						team=re.sub('[ \t\n\r\f\v]+On[ \t\n\r\f\v]+Ice[ \t\n\r\f\v]*$', '', cols[i])
						line=[]
						for playertag in tag_search(td, ['table', 'tr', 'td', 'table', 'tr', 'td', 'font']):
							number=get_string(playertag)
							position=re.sub('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*.*$', '', playertag.attrs['title'])
							player=re.sub('^.*[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*', '', playertag.attrs['title'])
							line.append(team+' #'+number+' '+player)
							if (debug_pl):
								print("   Player: "+str(len(line))+" = "+line[-1])
						event[cols[i]]=','.join(line)
					elif re.search('Time:ElapsedGame', cols[i]):
						event[cols[i]]=get_string(td)
						timesplit=event[cols[i]].split(':')
						event['Elapsed']=timesplit[0]+':'+timesplit[1][0:2]
						event['Remaining']=timesplit[1][2:]+':'+timesplit[2]
						if (debug_pl):
							print("   Elapsed="+event['Elapsed'])
							print("   Remaining="+event['Remaining'])
					else:
						event[cols[i]]=get_string(td)

					if (debug_pl):
						print("   "+str(i)+" -> "+cols[i]+" = "+event[cols[i]])

				if (debug_pl):
					debug(event)

				pl.append(event)
	return pl

def get_ro(game):
	url='http://www.nhl.com/scores/htmlreports/'+str(game['season'])+'/RO'+game['html']['t']+game['html']['n']+'.HTM'
	text=wget(url)
	if text is None:
		return None
	soup = BeautifulSoup(text, 'html.parser')
	if soup is None:
		return None
	ro={}
	debug=True

	teams=[]
	roots=[[0, 5, 3, 1, 1, 1], [1, 5, 5, 1, 1, 1], [1, 1, 5, 5, 1, 1, 1], [0, 5, 1, 1, 1, 1]]
	root=soup
#[document][0]->html[5]->body[3]->table[1]->tr[1]->td[1] ->table[1]->tr[1]->td[1]->table[1]->tr[1]->td[1]->table[3]->tr[1]->td[1]->table[1]->tr[1]->td[0]->img
#<img src=http://www.nhl.com/scores/htmlreports/images/logocvgk.gif alt=VEGAS GOLDEN KNIGHTS width=50 height=50 border=0>

#[document][0]->html[5]->body[3]->table[1]->tr[1]->td[1] ->table[1]->tr[1]->td[1]->table[1]->tr[5]->td[1]->table[3]->tr[1]->td[1]->table[1]->tr[5]->td[0]->img
#<img src=http://www.nhl.com/scores/htmlreports/images/logocedm.gif alt=EDMONTON OILERS width=50 height=50 border=0>

	teams=[]
	for rootra in roots:
		root=nav_tag(soup, rootra)
		if root is None:
			continue

		away=nav_tag(root, [1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 0]).attrs['src']
		if away is None:
			continue
		away=re.sub('^.*[lL][oO][gG][oO][aAcC]', '', away)
		away=re.sub('[0-9]*[.]gif$', '', away)
		away=away.upper()

		home=nav_tag(root, [1, 1, 1, 1, 5, 1, 3, 1, 1, 1, 5, 0]).attrs['src']
		home=re.sub('^.*[lL][oO][gG][oO][aAcC]', '', home)
		home=re.sub('[0-9]*[.]gif$', '', home)
		home=home.upper()
		if home is None:
			continue
		
		awayfull=get_string(nav_tag(root, [5, 1, 1, 1, 1]))
		homefull=get_string(nav_tag(root, [5, 1, 1, 1, 3]))
		if away != '' and home != '':
			teams=[away, home]

		if len(teams) > 0:
			print(','.join(teams))
			break
	if len(teams) == 0:
		debug_html(soup)
		print(str(game['gamePk'])+' failed to parse roster')
		return None

	rosters=[]
	rostertag=nav_tag(root, [7, 1, 1, 1])
	for td in tag_search(rostertag, ['td']):
		roster=[]
		labels=[]
		for table in tag_search(td, ['table']):
			for tr in tag_search(table, ['tr']):
				cols=[]
				for col in tag_search(tr, ['td']):
					cols.append(get_string(col))
				if len(labels) == 0:
					#French
					if cols[2] == 'Nom/Name':
						cols[2]='Name'
					labels=cols
				else:
					player={}
					for i in range(0, len(labels)):
						player[labels[i]]=cols[i]
					if 'Name' in player:
						if re.search('[ \t\n\r\f\v]+[(][CA][)][ \t\n\r\f\v]*$', player['Name']):
							captain=re.sub('^.*[(]', '', player['Name'])
							captain=re.sub('[)].*$', '', captain)

							player['Name']=re.sub('[ \t\n\r\f\v]+[(][^)]*[)][ \t\n\r\f\v]*$', '', player['Name'])
							player['Captain']=captain

						if 'class' in col.attrs:
							for c in col.attrs['class']:
								if c == 'bold':
									player['Start']=True
								elif c == 'italic':
									if 'Captain' not in player:
										debug_html(tr)
										json.dumps(player)
										print("Should be a captain!")
										return None
						player['Team']=teams[len(rosters)]
						if debug:
							print("Player:"+json.dumps(player))
						player['Scratched']=False
						roster.append(player)
		rosters.append(roster)
	ro['rosters']=rosters

	scratches=[]
	scratchtag=nav_tag(root, [7, 1, 1, 7])
	for td in tag_search(scratchtag, ['td']):
		roster=[]
		labels=[]
		for table in tag_search(td, ['table']):
			for tr in tag_search(table, ['tr']):
				cols=[]
				for col in tag_search(tr, ['td']):
					cols.append(get_string(col))
				if len(labels) == 0:
					#French
					if len(cols) >= 2 and cols[2] == 'Nom/Name':
						cols[2]='Name'
					labels=cols
				else:
					player={}
					for i in range(0, len(labels)):
						player[labels[i]]=cols[i]
					player['Scratched']=True
					player['Team']=teams[len(scratches)]
					if debug:
						print("Scratch:"+json.dumps(player))
					roster.append(player)
		scratches.append(roster)
	ro['scratches']=scratches

	coaches=[]
	for coachra in [[7, 1, 1, 13], [7, 1, 1, 7]]:
		coaches=[]
		coachtag=nav_tag(root, coachra)
		for td in tag_search(coachtag, ['td']):
			coach={}
			names=get_string(td).split('\n')
			coach['Name']=names[0]
			if re.search('#[ \t\n\r\f\v]*[0-9]+[ \t\n\r\f\v]+', coach['Name']):
				return None
			coach['Pos']='Head Coach'
			coach['Team']=teams[len(coaches)]
			if debug:
				print('Coach:'+json.dumps(coach))
			coaches.append(coach)
		ro['coaches']=coaches
		if len(coaches) == 2:
			break

	if len(coaches) != 2:
		debug_html(soup)
		print("Missing a coach!")
		print(json.dumps(game))
		return None

	officials=[]
	refs=[]
	lines=[]
	for refra in [[7, 1, 1, 19], [7, 1, 1, 13]]:
		refs=[]
		lines=[]
		reftag=nav_tag(root, refra)
		for td in tag_search(reftag, ['td']):
			for table in tag_search(td, ['table']):
				for tr in tag_search(table, ['tr']):
					reftag=nav_tag(tr, [1])
					if 'class' in reftag.attrs and reftag.attrs['class'][0]=='heading':
						refs.append(get_string(reftag))
						print("Ref type: "+refs[-1])
					else:
						for nametable in tag_search(reftag, ['table']):
							for nametr in tag_search(nametable, ['tr']):
								names=get_string(nametr).split('\n')
								refs.append(names[0])
								if debug:
									print("Ref name: "+refs[-1])

					linetag=nav_tag(tr, [3])
					if 'class' in linetag.attrs and linetag.attrs['class'][0]=='heading':
						lines.append(get_string(linetag))
						print("Line type: "+lines[-1])
					else:
						for nametable in tag_search(linetag, ['table']):
							for nametr in tag_search(nametable, ['tr']):
								names=get_string(nametr).split('\n')
								lines.append(names[-1])
								print("Line name: "+lines[-1])
		if len(refs) != 0 and len(lines)!=0:
			break

	if len(refs) == 0 and len(lines)==0:
		debug_html(soup)
		print("Refs failed to parse")
		print(collated['gamePk'])
		exit(0)

	for l in lines:
		refs.append(l)
	lines=[]

	title=''
	#2022/02/0714 - standby referee
	for l in refs:
		if re.search('^[ \t\n\r\f\v]*Referee[ \t\n\r\f\v]*$', l):
			title='REFEREE'
		elif re.search('^[ \t\n\r\f\v]*Arbitre/Referee[ \t\n\r\f\v]*$', l):
			title='REFEREE'
		elif re.search('^[ \t\n\r\f\v]*Linesman[ \t\n\r\f\v]*$', l):
			title='LINESMAN'
		elif re.search('^[ \t\n\r\f\v]*JL/Linesman[ \t\n\r\f\v]*$', l):
			title='LINESMAN'
		elif re.search('^[ \t\n\r\f\v]*Linesperson[ \t\n\r\f\v]*$', l):
			title='LINESMAN'
		elif re.search('^[ \t\n\r\f\v]*Standby[ \t\n\r\f\v]*$', l):
			if title == 'REFEREE':
				title='STANDBY_REF'
			elif title == 'LINESMAN':
				title='STANDBY_LINE'
			else:
				print("Unknown standby ref type!")
				return None
		elif re.search('^[ \t\n\r\f\v]*[#][0-9]+[ \t\n\r\f\v]+', l):
			if title == '':
				print("No title found for refs!")
				return None

			num=re.sub('^[ \t\n\r\f\v]*[#]', '', l)
			num=re.sub('[ \t\n\r\f\v]+.*$', '', num)

			name=re.sub('^[ \t\n\r\f\v]*[#][0-9]+[ \t\n\r\f\v]+', '', l)

			official={}
			official['Name']=name
			official['#']=num
			official['Pos']=title
			officials.append(official)
		elif not re.search('^[ \t\n\r\f\v]*$', l):
			print("Unknown line: "+l)
			return None

	ro['officials']=officials

	return ro


#populate collated['teams'][team] with team information
def get_teams(data, collated):
	collated['teams']={}
	collated['lookup']['teams']={}
	collated['exclude']['teams']={}
	collated=get_teams_pxp(data, collated)
	collated=get_teams_live(data, collated)
	return collated

def get_teams_live(data, collated):
	if 'LIVE' not in data:
		return collated
	collated['LIVE']=data['LIVE']
	return collated

def get_teams_pxp(data, collated):
	if 'PXP' not in data:
		return collated
	debug=False
	for teamloc in ['away', 'home']:
		print("   "+teamloc)
		print(json.dumps(data['PXP'][teamloc+'Team'], indent=3))
		if 'name' in data['PXP'][teamloc+'Team']:
			teamname=data['PXP'][teamloc+'Team']['name']
			if 'default' in teamname:
				teamname=teamname['default']
		elif 'placeName' in data['PXP'][teamloc+'Team'] and 'commonName' in data['PXP'][teamloc+'Team']:
			teamname=data['PXP'][teamloc+'Team']['placeName']['default']+" "+data['PXP'][teamloc+'Team']['commonName']['default']

		print("      Name: "+teamname)
		abv=data['PXP'][teamloc+'Team']['abbrev']
		print("      Abv : "+abv)
		teamid=data['PXP'][teamloc+'Team']['id']
		print("      Id  : "+str(teamid))

		key=teamloc
		targets=get_name_combos(teamname)
		targets.append(key)
		targets.append(teamloc)
		targets.append(teamloc+"Team")
		targets.append(str(teamid))
		targets.append(abv)

		for n in targets:
			if n in collated['lookup']['teams']:
				collated['exclude']['teams'][n]=True
				del(collated['lookup']['teams'][n])

		for t in targets:
			if t not in collated['exclude']['teams']:
				print("      Target: "+str(t))
				collated['lookup']['teams'][t]=key

		collated['teams'][teamloc]={}
		collated['teams'][teamloc]['name']=teamname
		collated['teams'][teamloc]['abv']=abv
		collated['teams'][teamloc]['id']=teamid

	return collated

def get_coaches(data, collated):
	collated['coaches']={}
	collated['lookup']['coaches']={}
	collated=get_coaches_pxp(data, collated)
	return collated

def get_coaches_live(data, collated):
	if 'LIVE' not in data:
		return collated
	return collated

def get_coaches_pxp(data, collated):
	if 'PXP' not in data:
		return collated
	for team in collated['teams']:
		team=team+"Team"
		gameinfoloc=None
		if 'summary' in data['PXP']:
			gameinfoloc='summary'
		elif 'matchup' in data['PXP']:
			gameinfoloc='matchup'
		name=data['PXP'][gameinfoloc]['gameInfo'][team]['headCoach']['default']

		key=name.upper()
		targets=get_name_combos(name)
		for n in targets:
			if n in collated['lookup']['coaches']:
				key=collated['lookup']['coaches'][n]
				break

		for t in targets:
			collated['lookup']['coaches'][t]=key

		if team not in collated['coaches']:
			collated['coaches'][team]={}
		if team not in collated['coaches'][team]:
			collated['coaches'][team][key]={}

		collated['coaches'][team][key]['PXP']=data['PXP'][gameinfoloc]['gameInfo'][team]['headCoach']
		collated['coaches'][team][key]['Name']=name
		collated['coaches'][team][key]['Pos']=['Head Coach']
		collated['coaches'][team][key]['Team']=team
	return collated

def get_coaches_ro(data, collated):
	for coachi in range(0, len(data['RO']['coaches'])):
		rocoach=data['RO']['coaches'][coachi]
		name=rocoach['Name']

		key=name.upper()
		targets=get_name_combos(name)
		for n in targets:
			if n in collated['lookup']['coaches']:
				key=collated['lookup']['coaches'][n]
				break

		for t in targets:
			collated['lookup']['coaches'][t]=key

		for team in collated['teams']:
			if rocoach['Team'] == collated['teams'][team]['abv']:
				if team not in collated['coaches']:
					collated['coaches'][team]={}
				if team not in collated['coaches'][team]:
					collated['coaches'][team][key]={}
				collated['coaches'][team][key]['RO']=rocoach
				break

	return collated

def get_officials(data, collated):
	collated['officials']={}
	collated['lookup']['officials']={}
	collated=get_officials_pxp(data, collated)
	return collated

def get_officials_live(data, collated):
	if 'LIVE' not in data:
		return collated
	return collated

def get_officials_pxp(data, collated):
	if 'PXP' not in data:
		return collated
	for refkey in ['referees', 'linesmen']:
		gameinfoloc=None
		if 'summary' in data['PXP']:
			gameinfoloc='summary'
		elif 'matchup' in data['PXP']:
			gameinfoloc='matchup'
		for name in data['PXP'][gameinfoloc]['gameInfo'][refkey]:
			name=name['default']
			key=name.upper()
			targets=get_name_combos(name)
			for n in targets:
				if n in collated['lookup']['officials']:
					key=collated['lookup']['officials'][n]
					break

			for t in targets:
				collated['lookup']['officials'][t]=key

			if key not in collated['officials']:
				collated['officials'][key]={}
			collated['officials'][key]['PXP']={}
			collated['officials'][key]['PXP']['Type']=refkey
			collated['officials'][key]['PXP']['Name']=name
			collated['officials'][key]['Type']=refkey
			collated['officials'][key]['Name']=name
	return collated

def get_officials_ro(data, collated):
	for i in range(0, len(data['RO']['officials'])):
		roofficial=data['RO']['officials'][i]

		if roofficial['Name'] == 'Francois StLaurent':
			roofficial['Name']='Francois St. Laurent'
		elif roofficial['Name'] == 'Justin StPierre':
			roofficial['Name']='Justin St. Pierre'
		name=roofficial['Name'].upper()

		key=roofficial['Name'].upper()
		targets=get_name_combos(name)
		for n in targets:
			if n in collated['lookup']['officials']:
				key=collated['lookup']['officials'][n]
				break

		for t in targets:
			collated['lookup']['officials'][t]=key

		if key not in collated['officials']:
			collated['officials'][key]={}
		collated['officials'][key]['RO']=roofficial

	return collated

def search_nhlid(searchstr):
	debug=False
	if debug:
		print("Search NHL: "+searchstr)
	searchstr=re.sub('^[ \t\n\r\f\v]*[.A-Z][.A-Z][.A-Z][ \t\n\r\f\v]+[#]?[ \t\n\r\f\v]*[0-9]+[ \t\n\r\f\v]+', '', searchstr)
	searchstr=unidecode(searchstr).upper()
	url="https://search.d3.nhle.com/api/v1/search/player?culture=en-us&q="+searchstr
	session=requests.Session()
	response=session.get(url)
	text=response.text
	results = json.loads(text)
	bestid = 0
	bestmatch = 0
	for result in results:
		id = result['playerId']
		name = unidecode(result['name']).upper()
		match=0
		for s in re.split('[ \t\n\r\f\v]+', searchstr):
			if re.search("(?i)"+s, name):
				print("   Found: "+s+" in "+name)
				match=match+1
			else:
				print("   No   : "+s+" in "+name)
		if match > bestmatch:
			bestid=id
			bestmatch=match
			print("   *** "+name+" ("+str(id)+") = "+str(match))
		else:
			print("       "+name+" ("+str(id)+") = "+str(match))
	return bestid

def get_nhlid(id):
	try:
		id = int(id)
	except ValueError as e:
		id = search_nhlid(id)
		pass

	url="https://api-web.nhle.com/v1/player/"+str(id)+"/landing"
	headers={}
	headers['Referer']='https://www.nhl.com'
	headers['Origin']='https://www.nhl.com'
	session=requests.Session()
	response=session.get(url, headers=headers)
	nhldata={}
	if response.status_code == 200:
		text=response.text
		nhldata = json.loads(text)
	return nhldata

def get_players(data, collated):
	collated['players']={}
	collated['lookup']['players']={}
	collated['exclude']['players']={}
	collated=get_players_pxp(data, collated)
	collated=get_players_live(data, collated)
	collated=get_players_ro(data, collated)
	collated=get_players_nhl(data, collated)

	for key in collated['players']:
		try:
			key=int(key)
		except TypeError as e:
			print(key)
			print(e)

		print(str(key))
		if 'Team' not in collated['players'][key]:
			if 'PXP' in collated['players'][key]:
				collated['players'][key]['Team']=collated['players'][key]['PXP']['Team']
			elif 'RO' in collated['players'][key]:
				collated['players'][key]['Team']=collated['players'][key]['RO']['Team']
			elif 'LIVE' in collated['players'][key] and 'liveData' in collated['players'][key]:
				collated['players'][key]['Team']=collated['players'][key]['LIVE']['liveData']['Team']
			elif 'LIVE' in collated['players'][key] and 'gameData' in collated['players'][key]:
				collated['players'][key]['Team']=collated['players'][key]['LIVE']['gameData']['currentTeam']['triCode']
			elif 'NHL' in collated['players'][key]:
				collated['players'][key]['Team']=collated['players'][key]['NHL']['currentTeamAbbrev']

		if 'Name' not in collated['players'][key]:
			collated['players'][key]['Name']=collated['players'][key]['Team']

			if 'RO' in collated['players'][key]:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" #"+collated['players'][key]['RO']['#']
			elif 'LIVE' in collated['players'][key] and 'liveData' in collated['players'][key]['LIVE'] and 'jerseyNumber' in collated['players'][key]['LIVE']['liveData']:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" #"+str(collated['players'][key]['LIVE']['liveData']['jerseyNumber'])
			elif 'LIVE' in collated['players'][key] and 'gameData' in collated['players'][key]['LIVE'] and 'primaryNumber' in collated['players'][key]['LIVE']['gameData']:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" #"+collated['players'][key]['LIVE']['gameData']['primaryNumber']
			elif 'NHL' in collated['players'][key] and 'sweaterNumber' in collated['players'][key]['NHL']:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" #"+str(collated['players'][key]['NHL']['sweaterNumber'])

			if 'PXP' in collated['players'][key]:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" "+collated['players'][key]['PXP']['firstName']['default']+" "+collated['players'][key]['PXP']['lastName']['default']
			elif 'LIVE' in collated['players'][key] and 'liveData' in collated['players'][key]['LIVE']:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" "+collated['players'][key]['LIVE']['liveData']['person']['fullName']
			elif 'LIVE' in collated['players'][key] and 'gameData' in collated['players'][key]['LIVE']:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" "+collated['players'][key]['LIVE']['gameData']['fullName']
			elif 'NHL' in collated['players'][key]:
				collated['players'][key]['Name']=collated['players'][key]['Name']+" "+collated['players'][key]['NHL']['firstName']+" "+collated['players'][key]['NHL']['lastName']
			elif 'RO' in collated['players'][key]:
				collated['players'][key]['Name']=collated['players'][key]['Name']+' '+collated['players'][key]['RO']['Name']

		if 'Position' not in collated['players'][key]:
			if 'PXP' in collated['players'][key] and 'Position' in collated['players'][key]['PXP']:
				collated['players'][key]['Position']=collated['players'][key]['PXP']['Position']
			elif 'RO' in collated['players'][key]:
				collated['players'][key]['Position']=collated['players'][key]['RO']['Pos']
			elif 'LIVE' in collated['players'][key] and 'liveData' in collated['players'][key]['LIVE'] and collated['players'][key]['LIVE']['liveData']['position']['code'] != 'N/A':
				collated['players'][key]['Position']=collated['players'][key]['LIVE']['liveData']['position']['code']
			elif 'LIVE' in collated['players'][key] and 'gameData' in collated['players'][key]['LIVE']:
				collated['players'][key]['Position']=collated['players'][key]['LIVE']['gameData']['primaryPosition']['abbreviation']

		if 'Hand' not in collated['players'][key]:
			if 'LIVE' in collated['players'][key] and 'liveData' in collated['players'][key] and 'shootsCatches' in collated['players'][key]['LIVE']['liveData']:
				collated['players'][key]['Hand']=collated['players'][key]['LIVE']['liveData']['person']['shootsCatches']
			elif 'LIVE' in collated['players'][key] and 'gameData' in collated['players'][key] and 'shootsCatches' in collated['players'][key]['LIVE']['gameData']:
				collated['players'][key]['Hand']=collated['players'][key]['LIVE']['gameData']['shootsCatches']
			elif 'NHL' in collated['players'][key] and 'shootsCatches' in collated['players'][key]['NHL']:
				collated['players'][key]['Hand']=collated['players'][key]['NHL']['shootsCatches']
			else:
				collated['players'][key]['Hand']="No idea"

		if 'Scratched' not in collated['players'][key] or not collated['players'][key]['Scratched']:
			if 'RO' in collated['players'][key]:
				collated['players'][key]['Scratched']=collated['players'][key]['RO']['Scratched']
			elif 'PXP' in collated['players'][key]:
				collated['players'][key]['Scratched']=collated['players'][key]['PXP']['Scratched']

	for k in collated['lookup']['players']:
		if re.search('CIRELLI', k):
			print("POST: "+str(k)+" -> "+str(collated['lookup']['players'][k]))
	print("Got players")

	return collated

def get_players_nhl(data, collated):
	for key in collated['players']:
		if 'NHL' not in collated['players'][key]:
			collated['players'][key]['NHL']=get_nhlid(key)

	return collated

def get_players_live(data, collated):
	if 'LIVE' not in data:
		return collated
	for idstr in data['LIVE']['gameData']['players']:
		player = data['LIVE']['gameData']['players'][idstr]
		nhlid=player['id']
		name=player['fullName']
		key=name
		position=player['primaryPosition']['code']
		for n in get_name_combos(key):
			if n in collated['exclude']['players']:
				continue
			elif n in collated['lookup']['players']:
				if collated['lookup']['players'][n] != nhlid:
					collated['exclude']['players'][n]=True
					del(collated['lookup']['players'][n])
					continue
			else:
				collated['lookup']['players'][n]=nhlid

		player['Scratched']=False
		player['Name']=name
		player['Position']=name

		if nhlid not in collated['players']:
			collated['players'][nhlid]={}
		if 'LIVE' not in collated['players'][nhlid]:
			collated['players'][nhlid]['LIVE']={}
		collated['players'][nhlid]['LIVE']['gameData']=player

	for teampos in data['LIVE']['liveData']['boxscore']['teams']:
		abv = data['LIVE']['liveData']['boxscore']['teams'][teampos]['team']['name']
		if 'triCode' in data['LIVE']['liveData']['boxscore']['teams'][teampos]['team']:
			abv = data['LIVE']['liveData']['boxscore']['teams'][teampos]['team']['triCode']
		for idstr in data['LIVE']['liveData']['boxscore']['teams'][teampos]['players']:
			player = data['LIVE']['liveData']['boxscore']['teams'][teampos]['players'][idstr]
			nhlid=player['person']['id']
			name=player['person']['fullName']
			key=abv+" "+name
			position=player['position']['code']

			for n in get_name_combos(key):
				if n in collated['exclude']['players']:
					continue
				elif n in collated['lookup']['players']:
					if collated['lookup']['players'][n] != nhlid:
						collated['exclude']['players'][n]=True
						del(collated['lookup']['players'][n])
						continue
				else:
					collated['lookup']['players'][n]=nhlid

			player['Scratched']=False
			player['Team']=abv
			player['Name']=name
			player['Position']=name

			if nhlid not in collated['players']:
				collated['players'][nhlid]={}
			if 'LIVE' not in collated['players'][nhlid]:
				collated['players'][nhlid]['LIVE']={}
			collated['players'][nhlid]['LIVE']['liveData']=player

	return collated

def get_players_pxp(data, collated):
	debugnames=[]
	debugids=[]
	debug=False
	if 'PXP' not in data:
		return collated

	for roster in data['PXP']['rosterSpots']:
		player=roster
		teamkey=collated['lookup']['teams'][str(roster['teamId'])]
		abv=collated['teams'][teamkey]['abv']
		name=abv+" #"+str(roster['sweaterNumber'])
		if 'default' in roster['firstName']:
			name=name+" "+roster['firstName']['default']
		else:
			name=name+" "+roster['firstName']

		if 'default' in roster['lastName']:
			name=name+" "+roster['lastName']['default']
		else:
			name=name+" "+roster['lastName']
		nhlid=roster['playerId']
		position=roster['positionCode']

		if type(player['firstName']) != type({}):
			tempname=player['firstName']
			player['firstName']={}
			player['firstName']['default']=tempname

		if type(player['lastName']) != type({}):
			tempname=player['lastName']
			player['lastName']={}
			player['lastName']['default']=tempname

		targets=get_name_combos(name)

		if len(debugnames) > 0:
			debug=False
			for dns in debugnames:
				for dn in get_name_combos(dns):
					for n in targets:
						if dn == n:
							debug=True
							break
					if debug:
						break
				if debug:
					break
		if not debug and len(debugids) > 0:
			debug=False
			for debugid in debugids:
				if debugid==nhlid:
					debug=True
					break

		if debug:
			print("PXP (dressed): "+name)
		for n in targets:
			if n in collated['exclude']['players']:
				if debug:
					print("   "+str(n)+" XXXX")
				continue
			elif n in collated['lookup']['players']:
				if collated['lookup']['players'][n] != nhlid:
					if debug:
						print("   "+str(n)+" -/-> "+str(nhlid))
					collated['exclude']['players'][n]=True
					del(collated['lookup']['players'][n])
			else:
				if debug:
					print("   "+str(n)+" ---> "+str(nhlid))
				collated['lookup']['players'][n]=nhlid

		if nhlid not in collated['players']:
			collated['players'][nhlid]={}
		if 'PXP' not in collated['players'][nhlid]:
			collated['players'][nhlid]['PXP']={}

		player['Scratched']=False
		player['Team']=abv
		player['Name']=name
		player['Position']=position

		collated['players'][nhlid]['PXP']=player

	for team in ['away', 'home']:
		teamkey=team+'Team'
		gameinfoloc=None
		if 'summary' in data['PXP']:
			gameinfoloc='summary'
		elif 'summary' in data['PXP']:
			gameinfoloc='matchup'
		else:
			return collated

		for scratch in data['PXP'][gameinfoloc]['gameInfo'][teamkey]['scratches']:
			if type(scratch['firstName']) != type({}):
				tempname=scratch['firstName']
				scratch['firstName']={}
				scratch['firstName']['default']=tempname

			if type(scratch['lastName']) != type({}):
				tempname=scratch['lastName']
				scratch['lastName']={}
				scratch['lastName']['default']=tempname

			abv=collated['teams'][team]['abv']
			name=abv+" "+scratch['firstName']['default']+' '+scratch['lastName']['default']
			nhlid=scratch['id']
			player=scratch
			player['Team']=abv
			player['Name']=name
			player['Scratched']=True
			#player['Position']=???

			targets=get_name_combos(name)

			if len(debugnames) > 0:
				debug=False
				for dns in debugnames:
					for dn in get_name_combos(dns):
						for n in targets:
							if dn == n:
								debug=True
								break
						if debug:
							break
					if debug:
						break
			if not debug and len(debugids) > 0:
				debug=False
				for debugid in debugids:
					if debugid==nhlid:
						debug=True
						break

			if debug:
				print("PXP (scratched): "+name)
			for n in targets:
				if n in collated['exclude']['players']:
					if debug:
						print("   Scratch: "+str(n)+" XXXX")
					continue
				elif n in collated['lookup']['players'] and collated['lookup']['players'][n] != nhlid:
					collated['exclude']['players'][n]=True
					del(collated['lookup']['players'][n])
					if debug:
						print("   Scratch: "+str(n)+" -/-> "+str(collated['lookup']['players'][n])+" != "+str(nhlid))
				else:
					collated['lookup']['players'][n]=nhlid
					if debug:
						print("   Scratch: "+str(n)+" ---> "+str(collated['lookup']['players'][n])+" != "+str(nhlid))

			if nhlid not in collated['players']:
				collated['players'][nhlid]={}
			if 'PXP' not in collated['players'][nhlid]:
				collated['players'][nhlid]['PXP']={}

			collated['players'][nhlid]['PXP']=player
	
	if 'matchup' in data['PXP']:
		for stat in data['PXP']['matchup']['teamLeadersL5']:
			for teampos in ['awayLeader', 'homeLeader']:
				for player in stat[teampos]:
					pass

		for teampos in data['PXP']['matchup']['goalieComparison']:
			for player in data['PXP']['matchup']['goalieComparison'][teampos]:
				pass
	
		for player in data['PXP']['matchup']['skaterSeasonStats']:
			pass
	
	#data['PXP']['shifts']['data']
	#data['PXP']['gameInfo']['referees']
	#data['PXP']['gameInfo']['linesmen']
	#data['PXP']['gameInfo']['awayTeam']['headCoach']['default']
	#data['PXP']['gameInfo']['awayTeam']['scratches']{id, ['firstName']['default'], ['lastName']['default']}
	#data['PXP']['gameInfo']['awayTeam']['scratches']{id, ['firstName']['default'], ['lastName']['default']}
	#data['PXP']['boxscore']['playerByGameStats']['homeTeam']['forwards'][]
	#data['PXP']['boxscore']['playerByGameStats']['homeTeam']['defense'][]
	#data['PXP']['boxscore']['playerByGameStats']['homeTeam']['goalies'][]{playerId, sweaterNumber, ['name']['default'], position}
	

	return collated

def get_players_ro(data, collated):
	debug=False
	debugnames=[]
	debugids=[]

	#Build name based lookup for RO
	namelookup={}
	nameexclude={}
	roplayers={}
	for rostertype in ['rosters', 'scratches']:
		for teami in range(0, len(data['RO'][rostertype])):
			for playeri in range(0, len(data['RO'][rostertype][teami])):
				player=data['RO'][rostertype][teami][playeri]

				if rostertype == 'scratches' or player['#'] == '0':
					player['Scratched']=True
				else:
					player['Scratched']=False

				if re.search('[ \t\n\r\f\v]*[(][C][)][ \t\n\r\f\v]*$', player['Name']):
					if not player['Scratched']:
						player['Captain']='C'
					player['Name'] = re.sub('[ \t\n\r\f\v]*[(][^)]*[)][ \t\n\r\f\v]*$', '', player['Name'])
				elif re.search('[ \t\n\r\f\v]*[(][A][)][ \t\n\r\f\v]*$', player['Name']):
					if not player['Scratched']:
						player['Alternate']='A'
					player['Name'] = re.sub('[ \t\n\r\f\v]*[(][^)]*[)][ \t\n\r\f\v]*$', '', player['Name'])

				key=player['Team']+' #'+player['#']+' '+player['Name']
				player['key']=key
				roplayers[key]=player

				subkeys=get_name_combos(key)

				if len(debugnames) > 0:
					debug=False
					for debugname in debugnames:
						for dn in get_name_combos(debugname):
							for sk in subkeys:
								if dn == sk:
									debug=True
									break
							if debug:
								break
				if debug:
					print("Start with "+key)

				for t in subkeys:
					if t in nameexclude:
						if debug:
							print("   "+t+" XXXX "+key)
						continue
					elif t in namelookup and namelookup[t] != key:
						if debug:
							print("   "+t+" -/-> "+key+" -/-> "+namelookup[t])
						nameexclude[t]=True
						del(namelookup[t])
					else:
						if debug:
							print("   "+t+" ---> "+key)
						namelookup[t]=key
	
	rekey=[]
	for key in roplayers:
		best={}
		print("Get ID for name: "+key)

		subkeys=get_name_combos(key)
		if len(debugnames) > 0:
			debug=False
			for debugname in debugnames:
				for dn in get_name_combos(debugname):
					for sk in subkeys:
						if dn == sk:
							debug=True
							break
					if debug:
						break
		if not debug and len(debugids) > 0:
			for sk in subkeys:
				for debugid in debugids:
					if sk in collated['lookup']['players'] and collated['lookup']['players'][sk] == debugid:
						debug=True
						break
				if debug:
					break

		for t in subkeys:
			if t in collated['exclude']['players']:
				if debug:
					print("   "+t+" XXXX by id")
			elif t in nameexclude:
				if debug:
					print("   "+t+" XXXX by name")
			elif t in collated['lookup']['players']:
				newkey=collated['lookup']['players'][t]
				if newkey not in best:
					best[newkey]=0
				best[newkey]=best[newkey]+1
				if debug:
					print("   "+t+" ---> "+str(newkey)+" ["+str(best[newkey]))
			elif debug:
				print("   "+t+" has no key")

		bestfit=sorted(best.items(), key=lambda x:x[1], reverse=True)
		if len(bestfit) == 1:
			bestid=bestfit[0][0]
			collated['players'][bestid]['RO']=roplayers[key]
			for t in get_name_combos(key):
				if t in collated['exclude']['players']:
					continue
				collated['lookup']['players'][t]=bestid
		elif len(bestfit) > 1:
			print("   Multiple possible ids")
			rekey.append(key)
		else:
			print("   Zero possible ids")
			rekey.append(key)

	for key in rekey:
		found=False
		for nhlid in collated['players']:
			if 'RO' in collated['players'][nhlid]:
				continue
			if 'PXP' in collated['players'][nhlid]:
				newid=None
				for firstk in collated['players'][nhlid]['PXP']['firstName']:
					first=collated['players'][nhlid]['PXP']['firstName'][firstk]
					for lastk in collated['players'][nhlid]['PXP']['lastName']:
						last=collated['players'][nhlid]['PXP']['lastName'][lastk]
						testname=collated['players'][nhlid]['PXP']['Team']+" "+first+" "+last
						for t in testname:
							if t in namelookup and namelookup[t] == key:
								print(testname+" ---> "+key+" ---> "+str(nhlid))
								if newid is None or newid == nhlid:
									newid=nhlid
									found=True
								else:
									print("Oh hell no")
									exit(79)
							if found:
								break
						if found:
							break
					if found:
						break
		if debug and not found:
			print('---------')
			for nhlid in collated['players']:
				if 'RO' in collated['players'][nhlid]:
					continue
				print(json.dumps(collated['players'][nhlid], indent=3))
			print('+++++++++')
			print(json.dumps(roplayers[key], indent=3))
			print('*********')
	
	return collated

def get_shifts(data, collated):
	for key in collated['players']:
		collated['players'][key]['shifts']={}

	print("   THV")
	collated=get_shifts_thv(data, collated)
	print("   PXP")
	collated=get_shifts_pxp(data, collated)
	print("   Merge")
	collated=merge_shifts(collated)
	print("   Done")
	return collated

def merge_shifts(collated):
	for key in collated['players']:
		if 'shifts' not in collated['players'][key]:
			continue

		print(str(key))
		shiftsbydt={}
		if 'THV' in collated['players'][key]['shifts']:
			print("   THV")
			i=0
			while i < len(collated['players'][key]['shifts']['THV']):
				thvshift=collated['players'][key]['shifts']['THV'][i]

				shift={}
				shift['StartDT']=decimaltime(thvshift['StartEL'], thvshift['Per'])
				shift['EndDT']=decimaltime(thvshift['EndEL'], thvshift['Per'])
				shift['nhlid']=key
				shift['THV']=thvshift

				if shift['StartDT'] not in shiftsbydt:
					shiftsbydt[shift['StartDT']]=[]

				found=None
				for j in range(0, len(shiftsbydt[shift['StartDT']])):
					compshift=shiftsbydt[shift['StartDT']][j]
					if compshift['EndDT'] != shift['EndDT']:
						continue
					if compshift['nhlid'] != shift['nhlid']:
						continue
					found=j
					break

				if found is None:
					shiftsbydt[shift['StartDT']].append(shift)
				else:
					shiftsbydt[shift['StartDT']][found]['THV']=thvshift

				i=i+1

		if 'PXP' in collated['players'][key]['shifts']:
			print("   PXP")
			i=0
			while i < len(collated['players'][key]['shifts']['PXP']):
				pxpshift=collated['players'][key]['shifts']['PXP'][i]

				shift={}
				shift['StartDT']=decimaltime(pxpshift['startTime'], pxpshift['period'])
				shift['EndDT']=decimaltime(pxpshift['endTime'], pxpshift['period'])
				shift['nhlid']=key
				shift['PXP']=pxpshift

				if shift['StartDT'] not in shiftsbydt:
					shiftsbydt[shift['StartDT']]=[]

				found=None
				for j in range(0, len(shiftsbydt[shift['StartDT']])):
					compshift=shiftsbydt[shift['StartDT']][j]
					if compshift['EndDT'] != shift['EndDT']:
						continue
					if compshift['nhlid'] != shift['nhlid']:
						continue
					found=j
					break

				if found is None:
					shiftsbydt[shift['StartDT']].append(shift)
				else:
					shiftsbydt[shift['StartDT']][found]['PXP']=pxpshift

				i=i+1

		#Delete the old shifts tree and replace it with the collated one
		print("   replace")
		found={}
		for shifttype in ['PXP', 'THV']:
			if shifttype in collated['players'][key]['shifts']:
				del(collated['players'][key]['shifts'][shifttype])
				found[shifttype]=True
		collated['players'][key]['shifts']=[]
		collated['players'][key]['shiftdiscard']=[]

		#Sort shifts by starting DT
		print("   sort")
		shifts=sorted(shiftsbydt.items(), key=lambda x:x[0])
		for tuple in shifts:
			missing=False
			for shifttype in found:
				if shifttype not in tuple[1][0]:
					missing=True
					break
			if not missing:
				collated['players'][key]['shifts'].append(tuple[1][0])
			else:
				collated['players'][key]['shiftdiscard'].append(tuple[1][0])

		#Find shifts which overlap by finding ones with a start before the
		#  current shift's end.
		print("   overlap")
		shifti=0
		while shifti < len(collated['players'][key]['shifts']):
			shift=collated['players'][key]['shifts'][shifti]
			shiftj=shifti+1
			while shiftj < len(collated['players'][key]['shifts']):
				overshift=collated['players'][key]['shifts'][shiftj]
				#This case can only happen if shifts are incorrectly sorted.
				#  That should never happen.
				if overshift['StartDT'] < shift['StartDT'] and overshift['EndDT'] < shift['StartDT']:
					shiftj=shiftj+1
					continue

				#This should mean that we're done because shifts should be
				#  sorted, so no further overshifts will have a start which
				#  overlaps
				if overshift['StartDT'] > shift['EndDT']:
					break

				#Trust THV over PXP
				if 'THV' in shift and 'THV' not in overshift:
					overshift['reason']="No THV"
					collated['players'][key]['shiftdiscard'].append(overshift)
					collated['players'][key]['shifts'].pop(shiftj)
					continue
				elif 'THV' in overshift and 'THV' not in shift:
					shift['reason']="No THV"
					collated['players'][key]['shiftdiscard'].append(shift)
					collated['players'][key]['shifts'].pop(shifti)
					shifti=shift-1
					break

				#THV in both.  Trust the one with PXP too.
				if 'PXP' in shift and 'PXP' not in overshift:
					overshift['reason']="Overlap with fewer sources"
					collated['players'][key]['shiftdiscard'].append(overshift)
					collated['players'][key]['shifts'].pop(shiftj)
					continue
				elif 'PXP' not in shift and 'PXP' in overshift:
					shift['reason']="Overlap with fewer sources"
					collated['players'][key]['shiftdiscard'].append(shift)
					collated['players'][key]['shifts'].pop(shifti)
					shifti=shifti-1
					break

				#Both have THV and PXP components.  So, absorb & merge?
				newshift={}
				if shift['StartDT'] < overshift['StartDT']:
					newshift['StartDT']=shift['StartDT']
				else:
					newshift['StartDT']=overshift['StartDT']

				if shift['EndDT'] > overshift['EndDT']:
					newshift['EndDT']=shift['EndDT']
				else:
					newshift['EndDT']=overshift['EndDT']

				if shift['nhlid'] != overshift['nhlid']:
					print("This player has shifts for two nhlids?!")
					exit(85)

				newshift['nhlid']=shift['nhlid']
				newshift['overlap']=[]
				newshift['overlap'].append(shift)
				if 'overlap' in shift:
					for e in shift['overlap']:
						newshift['overlap'].append(e)
					del(shift['overlap'])

				newshift['overlap'].append(overshift)
				if 'overlap' in overshift:
					for e in overshift['overlap']:
						newshift['overlap'].append(e)
					del(overshift['overlap'])

				collated['players'][key]['shifts'][shifti]=newshift
				collated['players'][key]['shifts'].pop(shiftj)
				shifti=shifti-1
				break

			shifti=shifti+1
		print("   done")

	return collated

def get_shifts_pxp(data, collated):
	if 'PXP' not in data:
		return collated
	
	for shift in data['PXP']['shifts']['data']:
		key = shift['playerId']
		if key is None:
			continue

		startdt=decimaltime(shift['startTime'], shift['period'])
		enddt=decimaltime(shift['startTime'], shift['period'])

		if key not in collated['players']:
			for k in collated['players']:
				print(str(k))
			print(key+" not found!")
			exit(9)
		if 'shifts' not in collated['players'][key]:
			collated['players'][key]['shifts']={}
		if 'PXP' not in collated['players'][key]['shifts']:
			collated['players'][key]['shifts']['PXP']=[]
		collated['players'][key]['shifts']['PXP'].append(shift)
		#period
		#endTime
		#startTime
		#duration
		#eventNumber
		#playerId
		#teamId
	return collated


def get_shifts_thv(data, collated):
	for player in data['TH']:
		player=re.sub('^[ \t\n\r\f\v]*', '', player)
		num=re.sub('[ \t\n\r\f\v]+.*$', '', player)
		name=re.sub('^[0-9]+[ \t\n\r\f\v]+', '', player)
		lookup=collated['teams']['home']['abv']+' #'+num+' '+name

		for n in get_name_combos(lookup):
			if n in collated['lookup']['players']:
				key = collated['lookup']['players'][n]
				collated['players'][key]['shifts']['THV']=data['TH'][player]
				break


	for player in data['TV']:
		player=re.sub('^[ \t\n\r\f\v]*', '', player)
		num=re.sub('[ \t\n\r\f\v]+.*$', '', player)
		name=re.sub('^[0-9]+[ \t\n\r\f\v]+', '', player)
		lookup=collated['teams']['away']['abv']+' #'+num+' '+name

		for n in get_name_combos(lookup):
			if n in collated['lookup']['players']:
				key = collated['lookup']['players'][n]
				collated['players'][key]['shifts']['THV']=data['TV'][player]
				break

	return collated

def get_decisions(data, collated):
	collated['decisions']={}

	lkey='L'
	lpoints=0
	wpoints=0
	if data['PXP']['gameType'] == 2:
		wpoints=2

		#Someday, I will need to add code here as the overtime loser point
		#   can be negated.  For example, if overtime ends from an empty net
		#   goal because the goalie was pulled and it wasn't in response to
		#   a delayed penalty.  See 2017/02/0156 and 2023/02/1023 for examples
		#   where the loser point could have been negated.
		if data['PXP']['periodDescriptor']['periodType'] != "REG":
			lkey='OTL'
			lpoints=1

	if data['PXP']['summary']['linescore']['totals']['away'] > data['PXP']['summary']['linescore']['totals']['home']:
		collated['decisions']['W']=data['PXP']['awayTeam']['abbrev']
		collated['decisions'][lkey]=data['PXP']['homeTeam']['abbrev']
	else:
		collated['decisions'][lkey]=data['PXP']['awayTeam']['abbrev']
		collated['decisions']['W']=data['PXP']['homeTeam']['abbrev']

	collated['decisions']['points']={}
	collated['decisions']['points'][collated['decisions']['W']]=wpoints
	collated['decisions']['points'][collated['decisions'][lkey]]=lpoints

	return collated

def print_shifts(collated, nhlid):
	print("Shifts for "+str(nhlid))
	if 'shifts' in collated['players'][int(nhlid)]:
		if type(collated['players'][int(nhlid)]['shifts']) == type([]):
			for shifti in range(0, len(collated['players'][int(nhlid)]['shifts'])):
				shift=collated['players'][int(nhlid)]['shifts'][shifti]
				if 'StartDT' not in shift or 'EndDT' not in shift:
					print(json.dumps(shift))
				elif 'PXP' in shift and 'THV' in shift:
					print("   "+str(shifti)+". "+undectime(shift['StartDT'])+" - "+undectime(shift['EndDT'])+" (THV, PXP)")
				elif 'PXP' in shift:
					print("   "+str(shifti)+". "+undectime(shift['StartDT'])+" - "+undectime(shift['EndDT'])+" (PXP)")
				elif 'THV' in shift:
					print("   "+str(shifti)+". "+undectime(shift['StartDT'])+" - "+undectime(shift['EndDT'])+" (THV)")
				elif 'generated' in shift:
					print("   "+str(shifti)+". "+undectime(shift['StartDT'])+" - "+undectime(shift['EndDT'])+" (generated)")
				else:
					print("   "+str(shifti)+". "+undectime(shift['StartDT'])+" - "+undectime(shift['EndDT']))
		else:
			print(json.dumps(collated['players'][int(nhlid)]['shifts'], indent=3))

def collate(data):
	data=fixgames(data)
	if data is None:
		return data
	f = open('predata.json', 'w')
	f.write(json.dumps(data))
	f.close()

	collated={}
	collated['lookup']={}
	collated['exclude']={}

	print("Get game info")
	collated = get_game_info(data, collated)
	print("Get team info")
	collated = get_teams(data, collated)
	print("Get coach info")
	collated = get_coaches(data, collated)
	print("Get ref info")
	collated = get_officials(data, collated)
	print("Get player info")
	collated = get_players(data, collated)
	print("Get shift info")
	collated = get_shifts(data, collated)
	print("Get star info")
	collated = get_decisions(data, collated)


	print("Get PL info")
	(data, collated)=parse_pl(data, collated)

	print("Merge to PL")
	collated=merge_loop(data, collated)

	collated['notes']=[]
	for note in data['PLNOTE']:
		if re.search('^[ \t\n\r\f\v]*[^,]+[,][ \t\n\r\f\v]+[^ ]+[ \t\n\r\f\v]+[0-9]+,[ \t\n\r\f\v]+[0-9]+[ \t\n\r\f\v]*$', note['Description']):
			note['Event']="DATE"
		elif re.search('^[ \t\n\r\f\v]*Attendance[ \t\n\r\f\v]+.*', note['Description']):
			note['Event']="ATND"
		elif re.search('^[ \t\n\r\f\v]*Start[ \t\n\r\f\v]+', note['Description']):
			note['Event']="TIME"
		elif re.search('^[ \t\n\r\f\v]*Game[ \t\n\r\f\v]+[0-9]+[ \t\n\r\f\v]*$', note['Description']):
			note['Event']="GAME"
		elif re.search('^[ \t\n\r\f\v]*Final[ \t\n\r\f\v]*$', note['Description']):
			note['Event']="FINAL"
		collated['notes'].insert(0, note)

	#collated['data']=data
	return collated

def find_player_ro(data, team, num, name):
	found=[]
	for k in ['rosters', 'scratches']:
		for i in range(0, len(data['RO'][k])):
			for j in range(0, len(data['RO'][k][i])):
				roentry=data['RO'][k][i][j]
				if str(roentry['Name']).upper() == name.upper() and roentry['Team'] == team:
					found.insert(0, ("RO", k, i, j))
	return found

def find_player_pxp(data, team, num, name):
	found=[]
	for teampos in ['awayTeam', 'homeTeam']:
		if data['PXP'][teampos]['abbrev'] != team:
			continue

		for i in range(0, len(data['PXP']['summary']['gameInfo'][teampos]['scratches'])):
			pxpentry=data['PXP']['summary']['gameInfo'][teampos]['scratches'][i]
			pxpname=""
			if type(pxpentry['firstName']) == type({}):
				pxpname=pxpentry['firstName']['default']
			else:
				pxpname=pxpentry['firstName']

			if type(pxpentry['lastName']) == type({}):
				pxpname=pxpname+" "+pxpentry['lastName']['default']
			else:
				pxpname=pxpname+" "+pxpentry['lastName']

			if pxpname.upper() == name.upper():
				found.insert(0, ("PXP", teampos, 'scratches', i))

		for i in range(0, len(data['PXP']['rosterSpots'])):
			pxpentry=data['PXP']['rosterSpots'][i]
			pxpname=""
			if type(pxpentry['firstName']) == type({}):
				pxpname=pxpentry['firstName']['default']
			else:
				pxpname=pxpentry['firstName']

			if type(pxpentry['lastName']) == type({}):
				pxpname=pxpname+" "+pxpentry['lastName']['default']
			else:
				pxpname=pxpname+" "+pxpentry['lastName']

			if pxpname.upper() == name.upper():
				found.insert(0, ("PXP", 'rosterSpots', i))
	return found

def rm_player(data, name):
	namera=re.split('[ \t\n\r\f\v]+', name)
	team=namera.pop(0)
	num=re.sub('[^0-9]+', '', namera.pop(0))
	if name.upper() == name:
		for i in range(2, len(namera)):
			namera[i]=namera[i].lower()
			namera[i][0]=namera[i][0].upper()
	name=' '.join(namera)

	for pathtuple in find_player_ro(data, team, num, name):
		if pathtuple[0] == 'RO':
			data[pathtuple[0]][pathtuple[1]][pathtuple[2]].pop(pathtuple[3])

	for pathtuple in find_player_pxp(data, team, num, name):
		if pathtuple[0] == 'PXP':
			if len(pathtuple) == 3:
				data[pathtuple[0]][pathtuple[1]].pop(pathtuple[2])
			elif len(pathtuple) == 4:
				data[pathtuple[0]]['summary']['gameInfo'][pathtuple[1]][pathtuple[2]].pop(pathtuple[3])
	return data

	for k in ['rosters', 'scratches']:
		for i in range(0, len(data['RO'][k])):
			remove=[]
			for j in range(0, len(data['RO'][k][i])):
				roentry=data['RO'][k][i][j]
				if str(roentry['Name']).upper() == name.upper() and roentry['Team'] == team:
					remove.insert(0, j)
			for j in remove:
				data['RO'][k][i].pop(j)

	for teampos in ['awayTeam', 'homeTeam']:
		if data['PXP'][teampos]['abbrev'] != team:
			continue

		remove=[]
		for i in range(0, len(data['PXP']['summary']['gameInfo'][teampos]['scratches'])):
			pxpentry=data['PXP']['summary']['gameInfo'][teampos]['scratches'][i]
			pxpname=""
			if type(pxpentry['firstName']) == type({}):
				pxpname=pxpentry['firstName']['default']
			else:
				pxpname=pxpentry['firstName']

			if type(pxpentry['lastName']) == type({}):
				pxpname=pxpname+" "+pxpentry['lastName']['default']
			else:
				pxpname=pxpname+" "+pxpentry['lastName']

			if pxpname.upper() == name.upper():
				remove.insert(0, i)
				break

		for i in remove:
			data['PXP']['summary']['gameInfo'][teampos]['scratches'].pop(i)

		remove=[]
		for i in range(0, len(data['PXP']['rosterSpots'])):
			pxpentry=data['PXP']['rosterSpots'][i]
			pxpname=""
			if type(pxpentry['firstName']) == type({}):
				pxpname=pxpentry['firstName']['default']
			else:
				pxpname=pxpentry['firstName']

			if type(pxpentry['lastName']) == type({}):
				pxpname=pxpname+" "+pxpentry['lastName']['default']
			else:
				pxpname=pxpname+" "+pxpentry['lastName']

			if pxpname.upper() == name.upper():
				remove.insert(0, i)
				break

		for i in remove:
			data['PXP']['rosterSpots'].pop(i)

	return data

def add_player(data, name, nhlid, pos="F", scratch=False):
	namera=re.split('[ \t\n\r\f\v]+', name)
	team=namera.pop(0)
	num=re.sub('[^0-9]+', '', namera.pop(0))
	if name.upper() == name:
		for i in range(2, len(namera)):
			namera[i]=namera[i].lower()
			namera[i][0]=namera[i][0].upper()

	roi=None
	for i in range(0, len(data['RO']['rosters'])):
		for j in range(0, len(data['RO']['rosters'][i])):
			if 'Team' in data['RO']['rosters'][i][j]:
				if data['RO']['rosters'][i][j]['Team'] == team:
					roi=i
				break
		if roi is not None:
			break

	pxpteampos=None
	for teampos in ['awayTeam', 'homeTeam']:
		if data['PXP'][teampos]['abbrev'] == team:
			pxpteampos=teampos
			break

	roentry={}
	roentry['#']='#'+str(num)
	roentry['Pos']=pos
	roentry['Name']=' '.join(namera)
	roentry['Team']=str(team)
	roentry['Scratched']=scratch
	if scratch:
		data['RO']['scratches'][roi].append(roentry)
	else:
		data['RO']['rosters'][roi].append(roentry)

	pxpentry={}
	pxpentry['firstName']={}
	pxpentry['firstName']['default']=namera.pop(0)
	pxpentry['lastName']={}
	pxpentry['lastName']['default']=' '.join(namera)
	if scratch:
		pxpentry['id']=int(nhlid)
		data['PXP'][pxpteampos]['scratches'].append(pxpentry)
	else:
		pxpentry['teamId']=int(data['PXP'][pxpteampos]['id'])
		pxpentry['playerId']=int(nhlid)
		pxpentry['sweaterNumber']=int(num)
		pxpentry['positionCode']=str(pos)
		pxpentry['headShot']="https://assets.nhle.com/mugs/nhl/"+str(data["GAME"]["season"])+"/"+str(team)+"/"+str(pxpentry['playerId'])+".png"
		data['PXP']['rosterSpots'].append(pxpentry)

	return data

def add_pl_stop(data, playi):
	event=data['PL'][playi]
	event['Event']="STOP"
	event['Description']="Unknown"
	event['fix']="Created"
	data['PL'].insert(playi, event)
	return data

def fixgames(data):
	#Season fixes
	if int(data['GAME']['gamePk']) < 2021010001:
		teamfix=False
		for i in range(0, len(data['PL'])):
			event=data['PL'][i]
			fixteams=['T.B', 'N.J', 'L.A', 'S.J']
			fixteamsre=['T[.]B', 'N[.]J', 'L[.]A', 'S[.]J']
			fixed=['TBL', 'NJD', 'LAK', 'SJS']
			for teami in range(0, len(fixteams)):
				print("Looking for "+fixteams[teami]+" On Ice")
				if fixteams[teami]+" On Ice" in event:
					teamfix=True
					event[fixed[teami]+" On Ice"]=re.sub(fixteamsre[teami]+" #", fixed[teami]+" #", event[fixteams[teami]+" On Ice"])
					del(event[fixteams[teami]+" On Ice"])
				event['OldDescription']=event['Description']
				event['Description']=re.sub(fixteamsre[teami], fixed[teami], event['OldDescription'])
			if teamfix == False:
				break

			data['PL'][i]=event

	#Game specific fixes
#	if int(data['GAME']['gamePk']) == 2023010013:
#		for playi in range(0, len(data['PL'])):
#			play=data['PL'][playi]
#			if play['Event'] == 'FAC' and play['Per'] == str(1) and play['Elapsed'] == "4:44":
#				data=add_pl_stop(data, playi)
	if int(data['GAME']['gamePk']) == 2022010048:
		print("Fixing up SEA #4 DANNY DEKEYSER")
		data=rm_player(data, "SEA #4 Danny DeKeyser")
		data=add_player(data, "VAN #4 Danny DeKeyser", 8477967, pos="C", scratch=False)

	elif int(data['GAME']['gamePk']) == 2021010032:
		data=add_player(data, "NSH #59 Nicholas Porco", 8481665, pos="LW", scratch=False)
	elif int(data['GAME']['gamePk']) == 2021010006:
		data=add_player(data, "NYI #64 Alex Jefferies", 8482154, pos="L", scratch=False)
	elif int(data['GAME']['gamePk']) == 2021010001:
		#This game has a trivial PL and can't be processed
		return None
	elif int(data['GAME']['gamePk']) == 2022010014:
		data['TV']["45 JAKE BISCHOFF"]=data['TV']["45 JAKE  BISCHOFF"]
		del(data['TV']["45 JAKE  BISCHOFF"])

		for teami in data['RO']:
			for player in data['RO'][teami]:
				if 'Name' not in player:
					continue
				if player['Name'] == "JAKE  BISCHOFF":
					player['Name'] = "JAKE BISCHOFF"
					break

		for playi in range(0, len(data['PL'])):
			play=data['PL'][playi]
			if 'VGK On Ice' not in play:
				continue
			play['VGK On Ice']=re.sub('VGK #45 JAKE  BISCHOFF', 'VGK #45 JAKE BISCHOFF', play['VGK On Ice'])
			data['PL'][playi]=play

#		if data['PXP']['plays'][-1]['typeDescKey'] != 'game-end':
#			event={}
#			for k in ['period', 'timeInPeriod', 'timeRemaining', 'homeTeamDefendingSide', 'sortOrder', 'situationCode']:
#				if k not in event:
#					continue
#				event[k]=data['PXP']['plays'][-1][k]
#			event['periodDescriptor']={}
#			for k in ['number', 'periodType']:
#				if k not in event['periodDescriptor']:
#					continue
#				event['periodDescriptor'][k]=data['PXP']['plays'][-1]['period']['periodDescriptor'][k]
#
#			event['eventId']=547
#			event['typeCode']=524
#			event['typeDescKey']='game-end'
#			event['sortOrder']=data['PXP']['plays'][-1]['sortOrder']+1
#			event['fix']='Created'
	elif int(data['GAME']['gamePk']) == 2022020310:
		for shifti in range(len(data['PXP']['shifts']['data'])-1, -1, -1):
			shift=data['PXP']['shifts']['data'][shifti]
			if shift['playerId'] == 8473575:
				data['PXP']['shifts']['data'].pop(shifti)
	elif int(data['GAME']['gamePk']) == 2022021053:
		for shifti in range(len(data['PXP']['shifts']['data'])-1, -1, -1):
			shift=data['PXP']['shifts']['data'][shifti]
			if shift['playerId'] == 8476433:
				data['PXP']['shifts']['data'].pop(shifti)
	elif int(data['GAME']['gamePk']) == 2021020741:
		for shifti in range(len(data['PXP']['shifts']['data'])-1, -1, -1):
			shift=data['PXP']['shifts']['data'][shifti]
			if shift['playerId'] == 8478039 and shift['period'] == 2:
				data['PXP']['shifts']['data'].pop(shifti)
	elif int(data['GAME']['gamePk']) == 2021021012:
		for shifti in range(len(data['PXP']['shifts']['data'])-1, -1, -1):
			shift=data['PXP']['shifts']['data'][shifti]
			if shift['playerId'] == 8478039:
				data['PXP']['shifts']['data'].pop(shifti)
	elif int(data['GAME']['gamePk']) == 2021021227:
		for shifti in range(len(data['PXP']['shifts']['data'])-1, -1, -1):
			shift=data['PXP']['shifts']['data'][shifti]
			if shift['playerId'] == 8475234:
				data['PXP']['shifts']['data'].pop(shifti)
	elif int(data['GAME']['gamePk']) == 2020020060:
		for shifti in range(len(data['PXP']['shifts']['data'])-1, -1, -1):
			shift=data['PXP']['shifts']['data'][shifti]
			if shift['playerId'] == 8470880:
				data['PXP']['shifts']['data'].pop(shifti)
	elif int(data['GAME']['gamePk']) == 2020020175:
		for shifti in range(len(data['PXP']['shifts']['data'])-1, -1, -1):
			shift=data['PXP']['shifts']['data'][shifti]
			if shift['playerId'] == 8475717:
				data['PXP']['shifts']['data'].pop(shifti)

#EGT, PGSTR, PGEND, ANTHEM, PSTR
#SOC, GOFF, GEND
	data['PL']=pl_period_markers(data['PL'])
	data['PL']=pl_game_markers(data['PL'])
	data['PXP']=pxp_game_markers(data['PXP'])
	return data


def pxp_game_markers(pxp):
	return pxp
	if len(pxp['plays']) == 0:
		return pxp

	gend=-1
	pend=-1
	for i in range(0, len(pxp['plays'])):
		play=pxp['plays'][i]
		if play['typeDescKey'] == 'game-end':
			gend=i
		elif play['typeDescKey'] == 'period-end':
			pend=i

	if gend == -1:
		print("No game-end found")
		newevent={}
		if pend != -1:
			newevent=pxp['plays'][pend]
			newevent['fix']='from pend'
		else:
			check=["period", "periodDescriptor", "timeInPeriod", "timeRemaining", "situationCode", "homeTeamDefendingSide"]
			for playi in range(len(pxp['plays'])-1, -1, -1):
				for fieldi in range(len(check)-1, -1, -1):
					if check[fieldi] in pxp['plays'][playi]:
						newevent[check[fieldi]]=pxp['plays'][playi][check[fieldi]]
						check.pop(fieldi)
			newevent['fix']='created'

		newevent['eventId']=767
		newevent['typeCode']=524
		newevent['typeDescKey']="game-end"
		newevent['sortOrder']=pxp['plays'][-1]['sortOrder']+1
		pxp['plays'].append(newevent)
#            {
#                "eventId": 767,
#                "period": 3,
#                "periodDescriptor": {
#                    "number": 3,
#                    "periodType": "REG"
#                },
#                "timeInPeriod": "20:00",
#                "timeRemaining": "00:00",
#                "situationCode": "1551",
#                "homeTeamDefendingSide": "left",
#                "typeCode": 524,
#                "typeDescKey": "game-end",
#                "sortOrder": 707
#            },
	else:
		event=pxp['plays'].pop(i)
		pxp['plays'].append(event)

	print(str(pxp['gameState'])+" == OFF/FINAL")
	print(str(pxp['gameScheduleState'])+" == OK")
	print(str(pxp['plays'][-1]['typeDescKey'])+" == shootout-complete/game-end")
	print(str(pxp['plays'][-1]['typeCode'])+" == 523, 524, 527")
	print(str(pxp['clock']['running'])+" == false")
	print(str(pxp['clock']['inIntermission'])+" == false")
	return pxp

def pl_game_markers(pl):
	return pl
	events={}
	find=['PGSTR', 'PGEND', 'ANTHEM', 'SOC', 'GOFF', 'GEND']
	for i in range(0, len(pl)):
		play=pl[i]
		if play['Event'] in find:
			events[play['Event']]=i

	for tuple in sorted(events.items(), key=lambda x:x[1], reverse=True):
		key = tuple[0]
		i = tuple[1]

		events[key]=pl.pop(i)
	
	for prefix in ['ANTHEM', 'PGEND', 'PGSTR']:
		if prefix not in events:
			continue
		pl.insert(0, events[prefix])
	
	for suffix in ['SOC', 'GOFF', 'GEND']:
		if suffix not in events:
			continue
		pl.append(events[suffix])

	return pl

def pl_period_markers(pl):
	return pl
	start=[None]
	end=[None]
	pstr=[False]
	pend=[False]
	for i in range(0, len(pl)):
		period=0
		play=pl[i]
		if 'Per' in play:
			period=int(play['Per'])
		else:
			continue

		if period >= len(start):
			start.insert(period, i)
			end.insert(period, i)
			pstr.insert(period, False)
			pend.insert(period, False)
		else:
			if play['Event'] == 'GEND':
				continue
			elif play['Event'] == 'GOFF':
				continue
			elif play['Event'] == 'SOC':
				continue
			end[period]=i

		if play['Event'] == 'PSTR':
			pstr[period]=True
		elif play['Event'] == 'PEND':
			pend[period]=True

	for period in range(len(pstr)-1, 0, -1):
		if not pend[period]:
			newplay=pl[pend[period]]
			newplay['Event']='PEND'
			newplay['Description']=''
			pl.insert(end[period], newplay)

		if not pstr[period]:
			newplay=pl[pstr[period]]
			newplay['Event']='PSTR'
			newplay['Description']=''
			pl.insert(start[period], newplay)

	return pl

def parsedesc(formatspec, desc, play, player_lookup):
	lastteam=None
	debug=False

	#if play['PLEvent'] == 'TAKE' and re.search('#24 JARVIS', play['PL']['Description']):
	#	debug=True

	if debug:
		print("Debug parsedesc starts:")
		print("format="+formatspec+"|")
		print("string="+desc+"|")

	while len(desc) > 0:
		template_match=re.search('[{][{][^{]*[}][}]', formatspec)
		if template_match is None:
			leading=formatspec[0:]
			discard=desc[0:]

			if debug:
				print("No more variables -- discarding")
				print("format="+leading+"|")
				print("string="+discard+"|")

			formatspec=''
			desc=''
		else:
			if template_match.start() > 0:
				leading=formatspec[0:template_match.start()]
				discard=desc[0:template_match.start()]
				desc=desc[template_match.start():]

				if debug:
					print("non-var text discarded:")
					print("format="+leading+"|")
					print("string="+discard+"|")
					print("  desc="+desc+"|")

				if leading != discard:
					desc=re.sub('^[ \t\n\r\f\v]+', '', desc)
					if debug:
						print("Leading space needs to get thrown out too?")
						print("  desc="+desc+"|")

			template=formatspec[(template_match.start()+2):(template_match.end()-2)]
			formatspec=formatspec[template_match.end():]
			if debug:
				print("   fmt={{"+template+"}}"+formatspec+"|")

			type_i=len(template)-2
			while template[type_i] != '|':
				type_i=type_i-1

			if debug:
				print("Var name = "+template[0:type_i])
				print("Var type = "+template[(type_i+1):])
			k=template[0:type_i]

			value_match=None
			if template[type_i+1:] == 'team':
				value_match=re.match('[-.A-Z][-.A-Z][-.A-Z]', desc)

			elif template[type_i+1:] == 'zone':
				value_match=re.match('[OND][fe][fu][.] Zone', desc)

			elif template[type_i+1:] == 'player':
				if debug:
					for match in re.findall('[0-9]+', desc):
						for similar in player_lookup:
							if re.search('(^|#|[ \t\n\r\f\v])'+re.escape(desc[template_match.start():template_match.end()])+'([ \t\n\r\f\v]|$)', similar):
								print("-"+similar+" = "+str(player_lookup[similar]))

				if debug:
					print("   Get block from "+formatspec)
				block=re.sub('[{][{].*$', '', formatspec)
				if debug:
					print("   Trimming to "+block)
				blockdesc=desc
				if re.search('[^ ]', block):
					blockdesc=re.sub(re.escape(block)+'.*$', '', desc)
					if debug:
						print("   Searching in "+blockdesc)
				ra=re.split('[ \t\n\r\f\v,()]+', blockdesc)
				if lastteam is not None and not re.match('[-.A-Z][-.A-Z][-.A-Z]', ra[0]):
					ra.insert(0, lastteam)

				i=1
				while i <= len(ra) and ' '.join(ra[0:i]) not in player_lookup:
					if debug:
						print('?'+' '.join(ra[0:i]))
					i=i+1

				while i <= len(ra) and ' '.join(ra[0:i]) in player_lookup:
					if debug:
						print('!'+' '.join(ra[0:i]))
					i=i+1

				if debug:
					print('*'+' '.join(ra[0:i]))
				i=i-1
				if debug:
					print("Value = "+' '.join(ra[0:i]))
				value_match = re.match('^.*?'+' '.join(ra[1:i]), desc)
				if value_match is None:
					value_match = re.match('[-.A-Z][-.A-Z][-.A-Z][ \t\n\r\f\v]+TEAM', desc)
					if debug:
						print("Special case for TEAM")
				if value_match is None:
					value_match = re.match('[-.A-Z][-.A-Z][-.A-Z][ \t\n\r\f\v]+[#]', desc)
					if debug:
						print("Special case for TEAM #")
				if value_match is None:
					value_match = re.match('[#]', desc)
					if debug:
						print("Special case for #")
				if debug:
					print("Final value = "+' '.join(ra[0:i]))
					print("            = "+desc[value_match.start():value_match.end()])

			elif template[type_i+1:] == 'time':
				value_match=re.match('[0-9]+[:][0-9]+[ \t\n\r\f\v]+[A-Z]+', desc)

			elif template[type_i+1:] == 'penalty':
				if debug:
					print("Starting as :"+desc)
				if re.search('[(]maj[)]', desc):
#					desc=re.sub('[(]maj[)]', '', desc)
					play['Severity']='major'
				if re.search('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*double[ \t\n\r\f\v]+minor[ \t\n\r\f\v]*[(]', desc):
#					desc=re.sub('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*double[ \t\n\r\f\v]+minor[ \t\n\r\f\v]*[(]', '(', desc)
					play['Severity']='double minor'
				if re.search('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*[mM]isconduct[ \t\n\r\f\v]*[(]', desc):
#					desc=re.sub('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*[mM]isconduct[ \t\n\r\f\v]*[(]', '(', desc)
					play['Severity']='misconduct'

				if re.search('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*[bB]ench[(]', desc):
#					desc=re.sub('[ \t\n\r\f\v]*[-][ \t\n\r\f\v]*[bB]ench[(]', '(', desc)
					if 'PenaltyOn' not in play:
						play['PenaltyOn']=['bench']

				if re.search('^PS[-]', desc):
#					desc=re.sub('^PS[-]', '', desc)
					play['Penalty Shot']=True

#				if re.search('[ \t\n\r\f\v]*on[ \t\n\r\f\v]+breakaway[ \t\n\r\f\v]*[(]', desc):
#					desc=re.sub('[ \t\n\r\f\v]*on[ \t\n\r\f\v]+breakaway[ \t\n\r\f\v]*[(]', '(', desc)

#				if re.search('([ \t\n\r\f\v]*[(][^)]*[)][ \t\n\r\f\v]*)*([(][^)]*[)])', desc):
#					desc=re.sub('([ \t\n\r\f\v]*[(][^)]*[)][ \t\n\r\f\v]*)*([(][^)]*[)])', r'\2', desc)

				if debug:
					print("Ending as :"+desc)

				penalty=penalty_type(desc)
				if penalty is not None:
					value_match=re.match(penalty, desc)
					if value_match is not None:
						t=re.sub('^.*[(]([0-9]+)[ \t\n\r\f\v]+min[)].*$', '\\1', desc)
						try:
							play['PIMs']=int(t)
						except ValueError as e:
							print("Starting with desc")
							print("PIMs == "+str(t))
							print("Non-numeric PIMs")
							exit(45)
					elif value_match is None:
						print(json.dumps(play))
						print("Unknown penalty type: "+desc)
						exit(104)

			elif template[type_i+1:] == 'shot':
#				types=['Backhand', 'Bat', 'Between Legs', 'Cradle', 'Deflected', 'Failed Attempt', 'Poke', 'Slap', 'Snap', 'Tip-In', 'Wrap-around', 'Wrist']
#				for type in types:
#					value_match=re.match(type, desc)
#					if value_match is not None:
#						break
				shot=shot_type(desc)
				value_match=re.match(shot, desc)
				if value_match is None:
					print("Looking for "+shot)
					print("Unknown shot type: "+desc)
					exit(105)

			elif template[type_i+1:] == 'miss':
				#types=['Goalpost', 'Hit Crossbar', 'Over Net', 'Wide of Net', 'Wide Left', 'Wide Right', 'Above Crossbar']
				#for type in types:
				#	value_match=re.match(type, desc)
				#	if value_match is not None:
				#		break
				miss=miss_type(desc)
				value_match=re.match(miss, desc)
				if value_match is None:
					print("Unknown miss type: "+desc)
					exit(106)

			elif template[type_i+1:] == 'distance':
				value_match=re.match('[0-9]+ ft[.]', desc)

			elif template[type_i+1:] == 'number':
				value_match=re.match('[0-9]+', desc)

			else:
				print("Unrecognized type "+template[type_i+1:])
				exit(107)

			if value_match is None:
				print("Couldn't find variable: "+template[type_i+1:])
				print("|"+desc+"|")
				exit(108)

			if debug:
				print('|'+desc+'|')
			value=desc[value_match.start():value_match.end()]
			if debug:
				print('-'+value+'|')
			desc=desc[value_match.end():]
			if debug:
				print('='+desc+'|')

			if template[type_i+1:] == 'player':
				if k not in play:
					play[k]=[]
				if not re.match('^[0-9]+$', value):
					if k == 'Shooter' and 'Shooter Team' in play:
						lookup=play['Shooter Team']+" "+value
						if lookup in player_lookup:
							value=player_lookup[lookup]
							if debug:
								print("Adjusting player value (by lookup) "+str(value)+" -> "+str(player_lookup[lookup]))
				play[k].append(value)
			else:
				play[k]=value

			if template[type_i+1:] == 'player' and play[k][-1] in player_lookup:
				if re.match('[-.A-Z][-.A-Z][-.A-Z][ \t\n\r\f\v]', play[k][-1]):
					lastteam=re.sub('[ \t\n\r\f\v].*$', '', play[k][-1])
				play[k][-1]=player_lookup[play[k][-1]]
			elif template[type_i+1:] == 'team':
				lastteam=play[k]
			if debug:
				print("Setting "+k+"="+str(play[k])+"|")
				print("Trimming to:"+desc)

	if debug:
		print("Debug parsedesc ended")
	return play

def parse_pl(data, collated):
	debug=False
	collated['plays']=[]

	#Parse all PL plays.  We'll use this as our definitive timeline
	for plplayi in range(0, len(data['PL'])):
		plplay=data['PL'][plplayi]
		play={}
		if plplay['Event'] == 'ANTHEM':
			pass
		elif plplay['Event'] == 'BLOCK':
			#EDM #93 NUGENT-HOPKINS BLOCKED BY  LAK #44 ANDERSON, Snap, Def. Zone
			#DET #23 RAYMOND OPPONENT-BLOCKED BY PIT #22 POULIN, Wrist, Def. Zone
			parsera=re.split(',', plplay['Description'])
			for i in range(0, len(parsera)):
				if re.search('[0-9]+[ \t\n\r\f\v]+ft[.]', parsera[i]):
					parsera[i]=re.sub('[0-9]+[ \t\n\r\f\v]+ft[.]', '{{Distance|distance}}', parsera[i])
				elif re.search('[ \t\n\r\f\v]+OPPONENT[-]BLOCKED[ \t\n\r\f\v]+BY[ \t\n\r\f\v]+', parsera[i]):
					shooter=re.sub('[ \t\n\r\f\v]+OPPONENT[-]BLOCKED[ \t\n\r\f\v]+BY.*$', '', parsera[i])
					shooter=re.sub('^[ \t\n\r\f\v]*', '', shooter)
					blocker=re.sub('^.*OPPONENT[-]BLOCKED[ \t\n\r\f\v]+BY[ \t\n\r\f\v]+', '', parsera[i])
					blocker=re.sub('[ \t\n\r\f\v]*$', '', blocker)
					parsera[i]=re.sub(shooter, '{{Shooter|player}}', parsera[i])
					if blocker != 'OTHER':
						parsera[i]=re.sub(blocker, '{{Blocker|player}}', parsera[i])
				elif re.search('[ \t\n\r\f\v]+TEAMMATE[-]BLOCKED[ \t\n\r\f\v]+BY[ \t\n\r\f\v]+', parsera[i]):
					shooter=re.sub('[ \t\n\r\f\v]+TEAMMATE[-]BLOCKED[ \t\n\r\f\v]+BY.*$', '', parsera[i])
					shooter=re.sub('^[ \t\n\r\f\v]*', '', shooter)
					blocker=re.sub('^.*TEAMMATE[-]BLOCKED[ \t\n\r\f\v]+BY[ \t\n\r\f\v]+', '', parsera[i])
					blocker=re.sub('[ \t\n\r\f\v]*$', '', blocker)
					parsera[i]=re.sub(shooter, '{{Shooter|player}}', parsera[i])
					if blocker != 'OTHER':
						parsera[i]=re.sub(blocker, '{{Blocker|player}}', parsera[i])
					parsera[i]=re.sub(shooter, '{{Shooter|player}}', parsera[i])
				elif re.search('[ \t\n\r\f\v]+BLOCKED BY[ \t\n\r\f\v]+', parsera[i]):
					shooter=re.sub('[ \t\n\r\f\v]+BLOCKED[ \t\n\r\f\v]+BY.*$', '', parsera[i])
					shooter=re.sub('^[ \t\n\r\f\v]*', '', shooter)
					blocker=re.sub('^.*[ \t\n\r\f\v]+BLOCKED[ \t\n\r\f\v]+BY[ \t\n\r\f\v]+', '', parsera[i])
					blocker=re.sub('[ \t\n\r\f\v]*$', '', blocker)
					parsera[i]=re.sub(shooter, '{{Shooter|player}}', parsera[i])
					if blocker != 'OTHER' and blocker != 'TEAMMATE':
						parsera[i]=re.sub(blocker, '{{Blocker|player}}', parsera[i])
				else:
					zone=zone_type(parsera[i])
					if zone is not None:
						parsera[i]=re.sub(zone, '{{SubZone|zone}}', parsera[i])
						continue

					shot=shot_type(parsera[i])
					if shot is not None:
						parsera[i]=re.sub(shot, '{{Shot|shot}}', parsera[i])
						continue

					if re.search('^[ \t\n\r\f\v]*Defensive[ \t\n\r\f\v]+Deflection[ \t\n\r\f\v]*$', parsera[i]):
						continue

					print("Unknown in BLOCK: "+parsera[i])
					exit(9)

			desc=','.join(parsera)
			if debug:
				print("Debug desc: "+desc)
			play=parsedesc(desc, plplay['Description'], play, collated['lookup']['players'])

		elif plplay['Event'] == 'CHL':
			pass
		elif plplay['Event'] == 'DELPEN':
			pass
		elif plplay['Event'] == 'EGPID':
			pass
		elif plplay['Event'] == 'EGT':
			pass
		elif plplay['Event'] == 'EISTR':
			pass
		elif plplay['Event'] == 'EIEND':
			pass
		elif plplay['Event'] == 'FAC':
			#EDM won Neu. Zone - EDM #97 MCDAVID vs LAK #24 DANAULT
			# - VGK #20 STEPHENSON vs DAL #18 DOMI
			#Neu. Zone - LAK #36 TYNAN vs ANA #39 CARRICK|


			homefo=re.sub('^.*[ \t\n\r\f\v]+vs[ \t\n\r\f\v]+', '', plplay['Description'])
			homefo=re.sub('[ \t\n\r\f\v]*$', '', homefo)
			awayfo=re.sub('[ \t\n\r\f\v]+vs[ \t\n\r\f\v]+.*$', '', plplay['Description'])
			awayfo=re.sub('^.*[ \t\n\r\f\v]+[-][ \t\n\r\f\v]+', '', awayfo)
			team=re.sub('[ \t\n\r\f\v]+won[ \t\n\r\f\v]+.*$', '', plplay['Description'])
			team=re.sub('^[ \t\n\r\f\v]*', '', team)
			zone=re.sub('[ \t\n\r\f\v]+[-][ \t\n\r\f\v]+.*$', '', plplay['Description'])
			zone=re.sub('^.*[ \t\n\r\f\v]+won[ \t\n\r\f\v]+', '', zone)

			desc=plplay['Description']
			if len(homefo) > 0:
				desc=re.sub(homefo, '{{HomeFO|player}}', desc, count=1)
			if len(awayfo) > 0:
				desc=re.sub(awayfo, '{{AwayFO|player}}', desc, count=1)
			if len(zone) > 0:
				desc=re.sub(zone, '{{SubZone|zone}}', desc, count=1)
			if len(team) > 0:
				desc=re.sub(team, '{{Winning Team|team}}', desc, count=1)

			play=parsedesc(desc, plplay['Description'], play, collated['lookup']['players'])

			if 'Winning Team' in play:
				if re.search('^'+play['Winning Team'], str(play['AwayFO'][0])):
					play['Winner']=play['AwayFO'][0]
					play['Loser']=play['HomeFO'][0]
				elif re.search('^'+play['Winning Team'], str(play['HomeFO'][0])):
					play['Winner']=play['HomeFO'][0]
					play['Loser']=play['AwayFO'][0]

		elif plplay['Event'] == 'GEND':
			pass
		elif plplay['Event'] == 'GIVE':
			#   LAK GIVEAWAY - #84 GAVRIKOV, Def. Zone
			play=parsedesc("{{Giving Team|team}} GIVEAWAY - {{Giver|player}}, {{SubZone|zone}}", plplay['Description'], play, collated['lookup']['players'])

		elif plplay['Event'] == 'GOAL':
			#LAK #19 IAFALLO(2), Wrist, Off. Zone, 12 ft.Assists: #3 ROY(2); #11 KOPITAR(4)

			parsera=re.split(',', plplay['Description'])
			for i in range(0, len(parsera)):
				change=False
				if re.search('Own Goal', parsera[i]):
					change=True
				elif re.search('Penalty Shot', parsera[i]):
					change=True

				if re.search('[0-9]+[ \t\n\r\f\v]+ft[.]', parsera[i]):
					change=True
					parsera[i]=re.sub('[0-9]+[ \t\n\r\f\v]+ft[.]', '{{Distance|distance}}', parsera[i])

				if re.search('Assists:[ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)][;][ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', parsera[i]):
					change=True
					parsera[i]=re.sub('Assists:[ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)][;][ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', 'Assists: {{Primary Assister|player}}({{Primary Assists|number}}); {{Secondary Assister|player}}({{Secondary Assists|number}})', parsera[i])
				elif re.search('Assist:[ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', parsera[i]):
					change=True
					parsera[i]=re.sub('Assist:[ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', "Assist: {{Primary Assister|player}}({{Primary Assists|number}})", parsera[i])
				elif re.search('^[ \t\n\r\f\v]*[A-Z.][A-Z.][A-Z.][ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', parsera[i]):
					change=True
					parsera[i]=re.sub('^[ \t\n\r\f\v]*[A-Z.][A-Z.][A-Z.][ \t\n\r\f\v]+[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', '{{Shooter|player}}({{ngoals|number}})', parsera[i])
				elif re.search('[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', parsera[i]):
					change=True
					parsera[i]=re.sub('[#][0-9]+[ \t\n\r\f\v]+[^(]+[(][0-9]+[)]', '{{Shooter|player}}({{ngoals|number}})', parsera[i])
				elif re.search('[#][0-9]+[ \t\n\r\f\v]+.*[^ ]', parsera[i]):
					change=True
					parsera[i]=re.sub('[#][0-9]+[ \t\n\r\f\v]+.*[^ ]', '{{Shooter|player}}', parsera[i])

				zone=zone_type(parsera[i])
				if zone is not None:
					change=True
					parsera[i]=re.sub(zone, '{{SubZone|zone}}', parsera[i])

				shot=shot_type(parsera[i])
				if shot is not None:
					change=True
					parsera[i]=re.sub(shot, '{{Shot|shot}}', parsera[i])

				if re.search('^[ \t\n\r\f\v]*Defensive[ \t\n\r\f\v]+Deflection[ \t\n\r\f\v]*$', parsera[i]):
					continue

				if not change:
					print(plplay['Description'])
					print(','.join(parsera))
					print("Unknown in GOAL: "+parsera[i])
					exit(9)

			desc=','.join(parsera)
			play=parsedesc(desc, plplay['Description'], play, collated['lookup']['players'])

		elif plplay['Event'] == 'GOFF':
			pass
		elif plplay['Event'] == 'HIT':
			#LAK #33 ARVIDSSON HIT EDM #14 EKHOLM, Off. Zone
			#TBL #40 DUMONT HIT NSH #5 BENNING, Off. Zone
			play=parsedesc("{{Hitter|player}} HIT {{Hittee|player}}, {{SubZone|zone}}", plplay['Description'], play, collated['lookup']['players'])

		elif plplay['Event'] == 'MISS':
			#EDM #2 BOUCHARD, Wrist, Wide of Net, Off. Zone, 55 ft.
			#EDM #55 HOLLOWAY, Penalty Shot, Backhand, Wide of Net, Off. Zone, 8 ft.
			#TOR # , Off. Zone, 24 ft.
			template=plplay['Description']
			zone=zone_type(template)
			if zone is not None:
				template=re.sub(zone, '{{SubZone|zone}}', template)

			shot=shot_type(template)
			if shot is not None:
				template=re.sub(shot, '{{Shot|shot}}', template)

			miss=miss_type(template)
			if miss is not None:
				template=re.sub(miss, '{{Missed|miss}}', template)

			#Defensive Deflection
			#Penalty Shot

			dist=re.search('[0-9]+[ \t\n\r\f\v]+ft[.]', template)
			if dist is not None:
				template=template[0:dist.start()]+'{{Distance|distance}}'+template[dist.end():]

			player=re.search('[A-Z][A-Z][A-Z][ \t\n\r\f\v]+#[^,]+', template)
			if player is not None:
				template=template[0:player.start()]+'{{Shooter|player}}'+template[player.end():]

			play=parsedesc(template, plplay['Description'], play, collated['lookup']['players'])
		elif plplay['Event'] == 'PBOX': #This event is jsut to denote that someone went to the penalty box
			pass
		elif plplay['Event'] == 'PEND':
			pass
		elif plplay['Event'] == 'PENL':
#			#VAN #47 JUULSEN ( min), Def. Zone Drawn By: PHI #14 COUTURIER
#			#desc=PIT #35 JARRY Butt ending - double minor(4 min) Served By: #43 HEINEN, #18 LAFFERTY, Neu. Zone Drawn By: NJD #55 GEERTSEN
#			#desc=CAR #20 AHO\u00a0Cross-checking(2 min) Served By: #13 PULJUJARVI, Def. Zone Drawn By: NJD #86 HUGHES
#			#ANA #26 MCGINN Interference(2 min) Drawn By: LAK #81 BOOTH
#CHI TEAM\u00a0Delay Game - Unsucc chlg(2 min) Served By: #94 PERRY, Neu. Zone
			desc=plplay['Description']
			print('Penalty start:'+desc+'|')
			if re.search('Drawn By: [A-Z][A-Z][A-Z][ \t\n\r\f\v]+#[ \t\n\r\f\v]*', desc):
				value_match=re.search('Drawn[ \t\n\r\f\v]+By:[ \t\n\r\f\v]*[A-Z][A-Z][A-Z][ \t\n\r\f\v]+#', desc)
				start=0
				end=len(desc)
				if value_match.start() is not None:
					start=value_match.start()+8
				while desc[start] != ':':
					start=start+1
				while desc[start] == ':':
					start=start+1
				while desc[start] == ' ':
					start=start+1
				if value_match.end() is not None:
					end=value_match.end()
				for j in range(len(desc), end, -1):
					if desc[start:j] in collated['lookup']['players']:
						desc=desc[0:start]+'{{DrawnBy|player}}'+desc[j:]
						break


			print('Post-Drawn:'+desc+'|')
			if re.search('Served By: [A-Z][A-Z][A-Z][ \t\n\r\f\v]+#[ \t\n\r\f\v]*', desc):
				value_match=re.search('Served[ \t\n\r\f\v]+By:[ \t\n\r\f\v]*[A-Z][A-Z][A-Z][ \t\n\r\f\v]+#', desc)
				start=0
				end=len(desc)
				if value_match.start() is not None:
					start=value_match.start()+9
				while desc[start] != ':':
					start=start+1
				while desc[start] == ':':
					start=start+1
				while desc[start] == ' ':
					start=start+1
				if value_match.end() is not None:
					end=value_match.end()
				for j in range(len(desc), end, -1):
					if desc[start:j] in collated['lookup']['players']:
						desc=desc[0:start]+'{{ServedBy|player}}'+desc[j:]
						break
			elif re.search('Served By:[ \t\n\r\f\v]*#[ \t\n\r\f\v]*', desc):
				value_match=re.search('Served[ \t\n\r\f\v]+By:[ \t\n\r\f\v]*#', desc)
				start=0
				end=len(desc)
				if value_match.start() is not None:
					start=value_match.start()+9
				while desc[start] != ':':
					start=start+1
				while desc[start] == ':':
					start=start+1
				while desc[start] == ' ':
					start=start+1
				if value_match.end() is not None:
					end=value_match.end()
				for j in range(len(desc), end, -1):
					if desc[start:j] in collated['lookup']['players']:
						desc=desc[0:start]+'{{ServedBy|player}}'+desc[j:]
						break

			print('Post-Served:'+desc+'|')
			if re.search('[A-Z][A-Z][A-Z][ \t\n\r\f\v]+#[ \t\n\r\f\v]*', desc):
				value_match=re.search('[A-Z][A-Z][A-Z][ \t\n\r\f\v]+#', desc)
				end=len(desc)
				if value_match.end() is not None:
					end=value_match.end()
				for j in range(len(desc), end, -1):
					if desc[value_match.start():j] in collated['lookup']['players']:
						desc=desc[0:value_match.start()]+'{{PenaltyOn|player}}'+desc[j:]
						break

			print('Post-On:'+desc+'|')
			zone=zone_type(desc)
			if zone is not None:
				value_match=re.search(zone, desc)
				value=desc[value_match.start():value_match.end()]
				desc=re.sub(value, '{{SubZone|zone}}', desc)

			print('Post-Zone:'+desc+'|')
			penalty=penalty_type(desc)
			if penalty is not None:
				value_match=re.search(penalty, desc)
				print("Penalty == |"+penalty+"|")
				start=0
				if value_match.start() is not None:
					start=value_match.start()
				end=len(desc)
				if value_match.end() is not None:
					end=value_match.end()
				value=desc[start:end]
				print("Match penalty as |"+value+"|")
				desc=re.sub(value, '{{Penalty|penalty}}', desc)

			print('Post-Parse:'+desc+'|')
			play=parsedesc(desc, plplay['Description'], play, collated['lookup']['players'])

#			desc=None
#			if re.search('^[-.A-Z][-.A-Z][-.A-Z][ \t\n\r\f\v]+TEAM', plplay['Description']):
#				desc=plplay['Description'][0:8]
#			elif re.search('^[-.A-Z][-.A-Z][-.A-Z][ \t\n\r\f\v]+#[ \t\n\r\f\v]+', plplay['Description']):
#				desc=plplay['Description'][0:6]
#			else:
#				desc="{{PenaltyOn|player}}"
#
#			if re.search('\u00a0', plplay['Description']):
#				re.sub('\u00a0', ' ', plplay['Description'])
#			desc=desc+" {{Penalty|penalty}}"
#
#			if re.search('Served By:', plplay['Description']):
#				servedtxt=re.sub('^.*Served By:[ \t\n\r\f\v]*', '', plplay['Description'])
#				servedtxt=re.sub(', [OND][fe][fu][.] Zone.*', '', servedtxt)
#				nserved=len(servedtxt.split(','))-1
#				desc=desc+" Served By: {{ServedBy|player}}"
#				while nserved > 0:
#					desc=desc+", {{ServedBy|player}}"
#					nserved=nserved-1
#
#			if re.search('[OND][ef][fu][.][ \t\n\r\f\v]+Zone', plplay['Description']):
#				desc=desc+", {{SubZone|zone}}"
#
#			if re.search('Drawn By:', plplay['Description']):
#				drawntxt=re.sub('^.*Drawn By:[ \t\n\r\f\v]*', '', plplay['Description'])
#				ndrawn=len(drawntxt.split(','))-1
#				desc=desc+" Drawn By: {{DrawnBy|player}}"
#				while ndrawn > 0:
#					desc=desc+", {{DrawnBy|player}}"
#					ndrawn=ndrawn-1


		elif plplay['Event'] == 'PGEND':
			pass
		elif plplay['Event'] == 'PGSTR':
			pass
		elif plplay['Event'] == 'PSTR':
			play=parsedesc("Period Start- Local time: {{Start|time}}", plplay['Description'], play, collated['lookup']['players'])
		elif plplay['Event'] == 'SHOT':
			#EDM ONGOAL - #97 MCDAVID, Wrist, Off. Zone, 11 ft.
			#DAL ONGOAL - # , 0 ft.
			#if re.search('Penalty[ \t\n\r\f\v]+Shot', plplay['Description']):
			#	play=parsedesc("{{Shooter Team|team}} ONGOAL - {{Shooter|player}}, Penalty Shot, {{Shot Type|shot}}, {{SubZone|zone}}, {{Distance|distance}}", plplay['Description'], play, collated['lookup']['players'])
			#	play['Reason']='Penalty Shot'
			#elif re.search('^[^,]*[,][^,]*$', plplay['Description']):
			#	play=parsedesc("{{Shooter Team|team}} ONGOAL - {{Shooter|player}}, {{Distance|distance}}", plplay['Description'], play, collated['lookup']['players'])
			#elif re.search('^[^,]*[,][^,]*[,][^,]*$', plplay['Description']):
			#	play=parsedesc("{{Shooter Team|team}} ONGOAL - {{Shooter|player}}, {{Shot Type|shot}}, {{Distance|distance}}", plplay['Description'], play, collated['lookup']['players'])
			#else:
			#	play=parsedesc("{{Shooter Team|team}} ONGOAL - {{Shooter|player}}, {{Shot Type|shot}}, {{SubZone|zone}}, {{Distance|distance}}", plplay['Description'], play, collated['lookup']['players'])

			template=plplay['Description']
			zone=zone_type(template)
			if zone is not None:
				template=re.sub(zone, '{{SubZone|zone}}', template)

			shot=shot_type(template)
			if shot is not None:
				template=re.sub(shot, '{{Shot|shot}}', template)

			#Defensive Deflection
			#Penalty Shot

			dist=re.search('[0-9]+[ \t\n\r\f\v]+ft[.]', template)
			if dist is not None:
				template=template[0:dist.start()]+'{{Distance|distance}}'+template[dist.end():]

			team=re.search('[A-Z][A-Z][A-Z][ \t\n\r\f\v]+ONGOAL', template)
			if team is not None:
				template=template[0:team.start()]+'{{Shooter Team|team}}'+template[team.start()+3:]

			player=re.search('#[^,]+', template)
			if player is not None:
				template=template[0:player.start()]+'{{Shooter|player}}'+template[player.end():]

			play=parsedesc(template, plplay['Description'], play, collated['lookup']['players'])

		elif plplay['Event'] == 'SOC':
			pass
		elif plplay['Event'] == 'STOP':
			pass
		elif plplay['Event'] == 'TAKE':
			play=parsedesc("{{Taking Team|team}} TAKEAWAY - {{Taker|player}}, {{SubZone|zone}}", plplay['Description'], play, collated['lookup']['players'])
		else:
			print(json.dumps(plplay, indent=3))
			print("Unknown PLEvent: "+plplay['Event'])
			print(str(data['GAME']['gamePk']))
			exit(109)

		for team in collated['teams']:
			break
			abv=collated['teams'][team]['abv']
			k=abv+' On Ice'
			if k in plplay:
				play[abv]=[]
				for player in plplay[k].split(','):
					id=None
					for n in get_name_combos(player):
						if n in collated['lookup']:
							id=collated['lookup'][n]
							play[abv].append(id)
							break

		if 'Per' not in plplay or re.search('^[ \t\n\r\f\v]*$', plplay['Per']):
			play['Period'] = 0
		else:
			play['Period'] = plplay['Per']
		play['Period'] = int(play['Period'])
		play['Elapsed'] = plplay['Elapsed']
		play['Remaining'] = plplay['Remaining']
		play['dt'] = decimaltime(play['Elapsed'], play['Period'])
		play['PLEvent']=plplay['Event']
		play['PL']=plplay
		collated['plays'].append(play)

	return (data, collated)

def build_toi_tree(collated):
	toitree={}
	poslookup={}
	for pos in collated['teams']:
		abv = collated['teams'][pos]['abv']
		poslookup[abv]=pos

	for nhlid in collated['players']:
		team=collated['players'][nhlid]['Team']
		teampos=poslookup[team]

		for i in range(0, len(collated['players'][nhlid]['shifts'])):
			shift=collated['players'][nhlid]['shifts'][i]
			if 'StartDT' in shift:
				onshift={}
				onshift['Shift']=i
				onshift['Player']=int(nhlid)
				onshift['Team']=team
				onshift['TeamPos']=teampos
				onshift['dt']=shift['StartDT']
				onshift['type']='on'

				if onshift['dt'] not in toitree:
					toitree[onshift['dt']]={}
				if teampos not in toitree[onshift['dt']]:
					toitree[onshift['dt']][teampos]={}
				if 'on' not in toitree[onshift['dt']][teampos]:
					toitree[onshift['dt']][teampos]['on']=[]
				toitree[onshift['dt']][teampos]['on'].append(onshift)

			if 'EndDT' in shift:
				offshift={}
				offshift['Shift']=i
				offshift['Player']=int(nhlid)
				offshift['Team']=team
				offshift['TeamPos']=teampos
				offshift['dt']=shift['EndDT']
				offshift['type']='off'

				if offshift['dt'] not in toitree:
					toitree[offshift['dt']]={}
				if teampos not in toitree[offshift['dt']]:
					toitree[offshift['dt']][teampos]={}
				if 'off' not in toitree[offshift['dt']][teampos]:
					toitree[offshift['dt']][teampos]['off']=[]
				toitree[offshift['dt']][teampos]['off'].append(offshift)
	
	return toitree

def add_icing(collated, playi):
	if 'icing' not in collated['temp']:
		collated['temp']['icing']=None

	play=collated['plays'][playi]
	if play['PLEvent'] == 'STOP':
		if 'PL' in play and 'Description' in play['PL'] and re.search('ICING', play['PL']['Description']):
			collated['temp']['icing']=playi
		elif 'PXP' in play and 'details' in play['PXP'] and 'reason' in play['PXP']['details'] and re.search('icing', play['PXP']['details']['reason']):
			collated['temp']['icing']=playi
	elif play['PLEvent'] == 'FAC':
		if collated['temp']['icing'] is None:
			return collated

		icedby="Unknown"
		if 'PXP' in play and 'details' in play['PXP'] and 'xCoord' in play['PXP']['details']:
			if play['PXP']['details']['xCoord'] < -50:
				if play['PXP']['homeTeamDefendingSide'] == 'left':
					icedby=collated['teams']['home']['abv']
				else:
					icedby=collated['teams']['away']['abv']
			elif play['PXP']['details']['xCoord'] > 50:
				if play['PXP']['homeTeamDefendingSide'] == 'right':
					icedby=collated['teams']['home']['abv']
				else:
					icedby=collated['teams']['away']['abv']
		elif 'SubZone' in play:
			if play['Winning Team'] == collated['teams']['home']['abv']:
				if play['SubZone'] == 'Def. Zone':
					icedby=collated['teams']['home']['abv']
				elif play['SubZone'] == 'Off. Zone':
					icedby=collated['teams']['away']['abv']
			else:
				if play['SubZone'] == 'Def. Zone':
					icedby=collated['teams']['away']['abv']
				elif play['SubZone'] == 'Off. Zone':
					icedby=collated['teams']['home']['abv']

		for i in range(collated['temp']['icing'], playi+1):
			collated['plays'][i]['icing']=icedby

	return collated

def add_zone(collated, playi):
	debug=False
	play=collated['plays'][playi]
	if 'SubZone' not in play:
		return collated
	if 'PL' not in play:
		return collated

#	if play['PLEvent'] == 'FAC':
#		if play['PL']['Winning Team'] == collated['teams']['away']['abv']

	if 'PXP' in play:
		if 'details' in play['PXP']:
			if 'xCoord' in play['PXP']['details']:
				if play['PXP']['details']['xCoord'] <= -30:
					play['Zone']='Left'
					if 'homeTeamDefendingSide' in play['PXP'] and play['PXP']['homeTeamDefendingSide'] == 'left':
						play[collated['teams']['home']['abv']]['Zone']='Def. Zone'
						play[collated['teams']['away']['abv']]['Zone']='Off. Zone'
					elif 'homeTeamDefendingSide' in play['PXP'] and play['PXP']['homeTeamDefendingSide'] == 'right':
						play[collated['teams']['home']['abv']]['Zone']='Off. Zone'
						play[collated['teams']['away']['abv']]['Zone']='Def. Zone'
				elif play['PXP']['details']['xCoord'] < 30:
					play['Zone']='Center'
					if 'homeTeamDefendingSide' in play['PXP']:
						play[collated['teams']['home']['abv']]['Zone']='Neu. Zone'
						play[collated['teams']['away']['abv']]['Zone']='Neu. Zone'
				else:
					play['Zone']='Right'
					if 'homeTeamDefendingSide' in play['PXP'] and play['PXP']['homeTeamDefendingSide'] == 'left':
						play[collated['teams']['home']['abv']]['Zone']='Def. Zone'
						play[collated['teams']['away']['abv']]['Zone']='Off. Zone'
					elif 'homeTeamDefendingSide' in play['PXP'] and play['PXP']['homeTeamDefendingSide'] == 'right':
						play[collated['teams']['home']['abv']]['Zone']='Off. Zone'
						play[collated['teams']['away']['abv']]['Zone']='Def. Zone'


				for k in play:
					if k == 'PXP':
						continue
					elif k == 'changes':
						continue
					if debug:
						print(json.dumps(play[k]))
				if debug:
					print(collated['teams']['home']['abv']+" == home")
					print("Zone == "+play['SubZone']+" == "+str(play['PXP']['details']['xCoord'])+", "+play['PXP']['homeTeamDefendingSide']+" -> "+play['Zone'])

	return collated

def add_empty_net(collated, playi):
	play=collated['plays'][playi]
	if 'Shooter' in play:
		for shooter in play['Shooter']:
			play['Shooter Team']=collated['players'][shooter]['Team']
		if 'Shooter Team' not in play:
			exit(6)

	for teampos in collated['teams']:
		abv=collated['teams'][teampos]['abv']
		if abv not in play:
			continue

		for nhlid in play[abv]['onice']:
			if collated['players'][int(nhlid)]['Position'] == 'G':
				play[abv]['Goalie']=nhlid

		play[abv]['Empty Net']=False
		if 'Goalie' not in play[abv]:
			play[abv]['Empty Net']=True

		if play['PLEvent'] == 'GOAL' or play['PLEvent'] == 'BLOCK' or play['PLEvent'] == 'MISS' or play['PLEvent'] == 'SHOT':
			if play['Shooter Team'] != abv and 'Goalie' not in play[abv]:
				play['Empty Net']=True
			else:
				play['Empty Net']=False

	collated['plays'][playi]=play
	return collated


def add_stops(collated, playi):
	if 'stop' not in collated['temp']:
		collated['temp']['stop']=True

	play = collated['plays'][playi]
	if play['PLEvent'] == 'FAC':
		if collated['temp']['stop'] == False:
			event={}
			for k in ['Period', 'Elapsed', 'Remaining', 'dt', 'PLPlay']:
				if k in play:
					event[k]=play[k]
			event['PLEvent']="STOP"
			event['fix']="created"
			event['Stopped']=True
			for teampos in collated['teams']:
				abv=collated['teams'][teampos]['abv']
				event[abv]=collated['plays'][playi-1][abv]

			reserve=[]
			while len(play['changes']) > 0 and play['changes'][-1]['dt'] == play['dt']:
				reserve.append(play['changes'].pop())
			play['changes'].append(event)
			while len(reserve) > 0:
				play['changes'].append(reserve.pop())

		collated['temp']['stop']=False
	else:
		for stopevent in ['EISTR', 'EIEND', 'GEND', 'GOAL', 'PEND', 'PENL', 'STOP']:
			if play['PLEvent'] == stopevent:
				collated['temp']['stop']=True
				break

	play['Stopped']=collated['temp']['stop']

	collated['plays'][playi]=play

	return collated

def add_strength(collated, playi):
	if 'Strength' not in collated['temp']:
		collated['temp']['Strength']="0v0"

	play=collated['plays'][playi]
	if 'changes' in play:
		for change in play['changes']:
			if 'Strength' in change:
				collated['temp']['Strength']=change['Strength']
	play['Strength']=collated['temp']['Strength']
	collated['plays'][playi]=play

	return collated

def merge_loop(data, collated):
	debug=False
	lastlive=0

	collated['temp']={}
	playi=0
	collated['temp']['toi']=build_toi_tree(collated)
	
	while playi < len(collated['plays']):
		print("Starting "+str(playi)+"/"+str(len(collated['plays'])))
		#Use lists of players to create off/stay/on
		if debug:
			print("   onice")
		collated=get_onice_one(collated, playi)

		#Use off/stay/on data to create changes with related TH/TV data
		if debug:
			print("   merge toi")
		collated=merge_toi_one(collated, playi)

		if debug:
			print("   merge live")
		collated=merge_pl_live_one(data, collated, playi)

		if debug:
			print("   merge pxp")
		collated=merge_pl_pxp_one(data, collated, playi)

		if debug:
			print("   add stops")
		collated=add_stops(collated, playi)

		if debug:
			print("   add strength")
		collated=add_strength(collated, playi)

		if debug:
			print("   add icing")
		collated=add_icing(collated, playi)

		if debug:
			print("   add zone")
		collated=add_zone(collated, playi)

		if debug:
			print("   add empty net info")
		collated=add_empty_net(collated, playi)

		if debug:
			print("Ending "+str(playi)+"/"+str(len(collated['plays'])))

		if 'changes' in collated['plays'][playi]:
			if debug:
				print("Adding changes from "+str(playi)+"/"+str(len(collated['plays'])))
			addplays=collated['plays'][playi]['changes']

			stopped=True
			if playi > 0:
				stopped=collated['plays'][playi-1]['Stopped']
			for change in addplays:
				change['Stopped']=stopped
				collated['plays'].insert(playi, change)
				playi=playi+1
			del(collated['plays'][playi]['changes'])

		playi=playi+1
	if debug:
		print("Done with plays")

	del(collated['temp'])

	return collated

def get_line_str(collated, line):
	linestr=""
	team=""
	if line == "":
		return line
	for nhlid in line.split(','):
		id=""
		if int(nhlid) in collated['players']:
			id = int(nhlid)
		elif str(nhlid) in collated['players']:
			id = str(nhlid)

		team = collated['players'][id]['Team']

		namenum=get_namenum(collated, id)
		#namenum=namenum+"("+collated['players'][id]['Position']+")"
		linestr=linestr+namenum+" "
	linestr=team+" "+linestr
	return linestr

def get_namenum(collated, nhlid):
	if nhlid in collated['players']:
		pass
	elif str(nhlid) in collated['players']:
		nhlid=str(nhlid)
	else:
		try:
			if int(nhlid) in collated['players']:
				nhlid=int(nhlid)
		except ValueError as e:
			return nhlid
			pass
	
	namenum=collated['players'][nhlid]['Name']
	namenum=re.sub('^[^#]*', '', namenum)
	namenum=re.sub('[ \t\n\r\f\v]*$', '', namenum)
	namenum=re.sub('[ \t\n\r\f\v].*[ \t\n\r\f\v]', ' ', namenum)
	return namenum

def print_play(collated, playi):
	play=collated['plays'][playi]
	line=str(play['dt'])+" "
	if 'PLEvent' in play:
		line=line+play['PLEvent']+'/'
	else:
		line=line+'???/'
	if 'LIVEEvent' in play:
		line=line+play['LIVEEvent']+' '
	else:
		line=line+'??? '

	flags=""
	if 'Stopped' in play and play['Stopped']:
		flags=flags+"S "
	if 'Icing' in play:
		flags=flags+"I("+play['Icing']+") "

	line=line+flags+" "
		

	if play['PLEvent'] == 'CHANGE':
		line=line+play['Team']+' '
		if 'off' in play:
			for p in play['off']:
				nhlid=p['Player']
				namenum=get_namenum(collated, nhlid)
				line = line+'-'+namenum+' '
		if 'stay' in play:
			for p in play['on']:
				nhlid=p['Player']
				namenum=get_namenum(collated, nhlid)
				line = line+'='+namenum+' '
		if 'on' in play:
			for p in play['on']:
				nhlid=p['Player']
				namenum=get_namenum(collated, nhlid)
				line = line+'+'+namenum+' '

	for teampos in collated['teams']:
		abv=collated['teams'][teampos]['abv']
		cl=""
		if 'off' in play[abv]:
			for nhlid in play[abv]['off']:
				namenum=get_namenum(collated, nhlid)
				cl = cl+'-'+namenum+' '
		if 'stay' in play[abv]:
			for nhlid in play[abv]['stay']:
				namenum=get_namenum(collated, nhlid)
				cl = cl+'='+namenum+' '
		if 'on' in play[abv]:
			for nhlid in play[abv]['on']:
				namenum=get_namenum(collated, nhlid)
				cl = cl+'+'+namenum+' '
		if cl != "":
			line=line+"\n   "+abv+" "+cl
					
	print(line)

def get_onice_one(collated, playi):
	debug=False
	play=collated['plays'][playi]
	if debug:
		print(str(play['Period'])+" "+play['Elapsed']+" - "+play['PLEvent'])

	onice={}
	oldonice={}
	for teampos in ['away', 'home']:
		abv=collated['teams'][teampos]['abv']
		onice[abv]={}
		oldonice[abv]={}

		if abv not in play:
			play[abv]={}
		if 'onice' not in play[abv]:
			play[abv]['onice']={}
		if 'on' not in play[abv]:
			play[abv]['on']=[]
		if 'stay' not in play[abv]:
			play[abv]['stay']=[]
		if 'off' not in play[abv]:
			play[abv]['off']=[]

	if playi > 0:
		oldplay = collated['plays'][playi-1]
		for teampos in ['away', 'home']:
			abv=collated['teams'][teampos]['abv']
			if abv in oldplay and 'onice' in oldplay[abv]:
				for p in oldplay[abv]['onice']:
					if debug:
						print("   Start: "+abv+" "+str(p))
					if p != '':
						oldonice[abv][p]=oldplay[abv]['onice'][p]

	for teampos in ['away', 'home']:
		abv=collated['teams'][teampos]['abv']
		if 'PL' in play:
			k = abv+' On Ice'
			if k in play['PL']:
				for n in play['PL'][k].split(','):
					nhlid=str(n)
					if n == '':
						continue
					if re.match('^[ \t\n\r\f\v]*[0-9]+[ \t\n\r\f\v]*$', n):
						pass
					elif n in collated['exclude']['players']:
						continue
					elif n in collated['lookup']['players']:
						nhlid=str(collated['lookup']['players'][n])
					elif n == "":
						continue
					else:
						for nf in get_name_combos(n):
							if nf in collated['exclude']['players']:
								continue
							if nf in collated['lookup']['players']:
								print(str(nf)+" -> "+str(collated['lookup']['players'][nf]))
						print("No lookup for "+n)
						print("Game: "+str(collated['GAME']['gamePk']))
						exit(132)

					if debug:
						print("    Play: "+abv+" "+str(nhlid))
					if nhlid in oldonice[abv]:
						onice[abv][nhlid]=oldonice[abv][nhlid]
					else:
						onice[abv][nhlid]=play['dt']
		if 'PXP' in play and 'details' in play['PXP']:
			for playerkey in ['playerId']:
				if playerkey in play['PXP']['details']:
					nhlid=play['PXP']['details'][playerkey]
					abv=collated['players'][int(nhlid)]['Team']
					if debug:
						if nhlid not in onice[abv]:
							print("    PXP: "+abv+" "+str(nhlid))
					if nhlid in oldonice[abv]:
						onice[abv][nhlid]=oldonice[abv][nhlid]
					else:
						onice[abv][nhlid]=play['dt']

	for abv in onice:
		if '' in oldonice[abv]:
			del(oldonice[abv][''])
		if '' in onice[abv]:
			del(onice[abv][''])
		play[abv]['onice']=onice[abv]

		for nhlid in oldonice[abv]:
			if nhlid in onice[abv]:
				play[abv]['stay'].append(nhlid)
				if debug:
					print("       = "+abv+" "+str(nhlid))
			else:
				play[abv]['off'].append(nhlid)
				if debug:
					print("       - "+abv+" "+str(nhlid))

		for nhlid in onice[abv]:
			if nhlid not in oldonice[abv]:
				play[abv]['on'].append(nhlid)
				if debug:
					print("       + "+abv+" "+str(nhlid))

	if debug:
		print("--- get_onice_one")
		if play['PLEvent'] == 'PSTR':
			sys.stdin.readline()
	collated['plays'][playi]=play

	return collated

def merge_toi_one(collated, playi):
	debug=True
	play=collated['plays'][playi]
	play['changes']=[]

	if 'onice' not in collated['temp']:
		collated['temp']['onice']={}
		for teampos in collated['teams']:
			abv = collated['teams'][teampos]['abv']
			collated['temp']['onice'][abv]={}

	dts=sorted(list(collated['temp']['toi']))
	for dt in dts:
		if dt >= play['dt']:
			break
		if debug:
			print(str(dt))
		strengthstart=len(play['changes'])
		for teampos in ['away', 'home']:
			if teampos not in collated['temp']['toi'][dt]:
				continue
			change={}
			change['PLEvent']="CHANGE"
			change['Period']=play['Period']
			change['Team']=collated['teams'][teampos]['abv']
			change['TeamPos']=teampos
			change['dt']=dt
			if debug:
				print("   "+teampos+" = "+change['Team'])
			for shifttype in ['off', 'on']:
				if shifttype not in change:
					change[shifttype]=[]
				if shifttype not in collated['temp']['toi'][dt][teampos]:
					continue
				if debug:
					print("      "+shifttype)
				remove=[]
				for shifti in range(0, len(collated['temp']['toi'][dt][teampos][shifttype])):
					shift=collated['temp']['toi'][dt][teampos][shifttype][shifti]
					if shifttype == 'off':
						if int(shift['Player']) not in collated['temp']['onice'][change['Team']]:
							if debug:
								print("         - "+str(shift['Player'])+" - skipped")
							continue
						del(collated['temp']['onice'][change['Team']][shift['Player']])
						if debug:
							print("         - "+str(shift['Player']))
					if shifttype == 'on':
						if int(shift['Player']) in collated['temp']['onice'][change['Team']]:
							if debug:
								print("         + "+str(shift['Player'])+" - skipped")
							continue
						collated['temp']['onice'][change['Team']][int(shift['Player'])]=dt
						if debug:
							print("         + "+str(shift['Player'])+" = "+str(collated['temp']['onice'][change['Team']][shift['Player']]))

					info={}
					info['Player']=shift['Player']
					info['Shift']=shift['Shift']
					change[shifttype].append(info)
					remove.insert(0, shifti)
				for shifti in remove:
					if debug:
						rmshift = collated['temp']['toi'][dt][teampos][shifttype][shifti]
						print("      Removing "+shifttype+": "+str(rmshift['Player']))
					del(collated['temp']['toi'][dt][teampos][shifttype][shifti])

				if len(collated['temp']['toi'][dt][teampos][shifttype]) == 0:
					del(collated['temp']['toi'][dt][teampos][shifttype])
			if len(list(collated['temp']['toi'][dt][teampos])) == 0:
				del(collated['temp']['toi'][dt][teampos])
			if len(change['on']) > 0 or len(change['off']) > 0:
				for oniceteam in ['away', 'home']:
					oniceabv=collated['teams'][oniceteam]['abv']
					change[oniceabv]={}
					change[oniceabv]['onice']={}
					for nhlid in collated['temp']['onice'][oniceabv]:
						change[oniceabv]['onice'][int(nhlid)]=collated['temp']['onice'][oniceabv][nhlid]
				play['changes'].append(change)
		for changei in range(strengthstart, len(play['changes'])):
			strength=[]
			if play['changes'][changei]['TeamPos'] == 'home':
				strength.insert(0, collated['teams']['home']['abv'])
				strength.insert(1, collated['teams']['away']['abv'])
			elif play['changes'][changei]['TeamPos'] == 'away':
				strength.insert(0, collated['teams']['away']['abv'])
				strength.insert(1, collated['teams']['home']['abv'])
			else:
				print("Unknown teampos: "+play['changes'][changei]['TeamPos'])
				exit(81)
			strength[0]=len(list(collated['temp']['onice'][strength[0]]))
			strength[1]=len(list(collated['temp']['onice'][strength[1]]))
			play['changes'][changei]['Strength']=str(strength[0])+'v'+str(strength[1])
		if len(list(collated['temp']['toi'][dt])) == 0:
			del(collated['temp']['toi'][dt])

	if play['dt'] in collated['temp']['toi']:
		if debug:
			print(str(play['dt'])+" == ")
		strengthstart=len(play['changes'])
		for teampos in ['away', 'home']:
			if teampos not in collated['temp']['toi'][play['dt']]:
				continue
			change={}
			change['PLEvent']="CHANGE"
			change['Period']=play['Period']
			change['Elapsed']=play['Elapsed']
			change['Remaining']=play['Remaining']
			change['Team']=collated['teams'][teampos]['abv']
			change['TeamPos']=teampos
			change['dt']=play['dt']
			change['on']=[]
			change['off']=[]
			if debug:
				print("   "+teampos+" = "+change['Team'])

			target={}
			for nhlid in play[change['Team']]['onice']:
				target[int(nhlid)]=True
				if debug and int(nhlid) in list(collated['temp']['onice'][change['Team']]):
					print("       Keeping "+str(nhlid))

			for nhlid in list(collated['temp']['onice'][change['Team']]):
				if int(nhlid) in target:
					continue
				if debug:
					print("       Need off for "+str(nhlid))
				if 'off' in collated['temp']['toi'][play['dt']][teampos]:
					for shifti in range(0, len(collated['temp']['toi'][play['dt']][teampos]['off'])):
						shift=collated['temp']['toi'][play['dt']][teampos]['off'][shifti]
						if int(shift['Player']) == int(nhlid):
							if debug:
								print("            "+str(shifti)+"/"+str(len(collated['temp']['toi'][play['dt']][teampos]['off']))+" will be advanced")
							del(collated['temp']['onice'][change['Team']][int(nhlid)])
							info={}
							info['Player']=int(shift['Player'])
							info['Shift']=shift['Shift']
							change['off'].append(info)
							del(collated['temp']['toi'][play['dt']][teampos]['off'][shifti])
							break
					if len(collated['temp']['toi'][play['dt']][teampos]['off']) == 0:
						del(collated['temp']['toi'][play['dt']][teampos]['off'])
				if int(nhlid) in collated['temp']['onice'][change['Team']]:
					#generate
					pass

			for nhlid in target:
				if int(nhlid) in collated['temp']['onice'][change['Team']]:
					continue
				if debug:
					print("       Need on for "+str(nhlid))
				if 'on' in collated['temp']['toi'][play['dt']][teampos]:
					for shifti in range(0, len(collated['temp']['toi'][play['dt']][teampos]['on'])):
						shift=collated['temp']['toi'][play['dt']][teampos]['on'][shifti]
						if int(shift['Player']) == int(nhlid):
							if debug:
								print("            "+str(shifti)+"/"+str(len(collated['temp']['toi'][play['dt']][teampos]['on']))+" will be advanced")
							collated['temp']['onice'][change['Team']][int(nhlid)]=play['dt']
							info={}
							info['Player']=int(shift['Player'])
							info['Shift']=shift['Shift']
							change['on'].append(info)
							del(collated['temp']['toi'][play['dt']][teampos]['on'][shifti])
							break
					if len(collated['temp']['toi'][play['dt']][teampos]['on']) == 0:
						del(collated['temp']['toi'][play['dt']][teampos]['on'])
				if int(nhlid) not in collated['temp']['onice'][change['Team']]:
					#generate
					pass

			if len(change['on']) > 0 or len(change['off']) > 0:
				for oniceteam in ['away', 'home']:
					oniceabv=collated['teams'][oniceteam]['abv']
					change[oniceabv]={}
					change[oniceabv]['onice']={}
					for nhlid in collated['temp']['onice'][oniceabv]:
						change[oniceabv]['onice'][int(nhlid)]=collated['temp']['onice'][oniceabv][nhlid]
				play['changes'].append(change)
			if len(list(collated['temp']['toi'][play['dt']][teampos])) == 0:
				del(collated['temp']['toi'][play['dt']][teampos])

		for changei in range(strengthstart, len(play['changes'])):
			strength=[]
			if play['changes'][changei]['TeamPos'] == 'home':
				strength.insert(0, collated['teams']['home']['abv'])
				strength.insert(1, collated['teams']['away']['abv'])
			elif play['changes'][changei]['TeamPos'] == 'away':
				strength.insert(0, collated['teams']['away']['abv'])
				strength.insert(1, collated['teams']['home']['abv'])
			else:
				print("Unknown teampos: "+play['changes'][changei]['TeamPos'])
				exit(82)
			strength[0]=len(list(collated['temp']['onice'][strength[0]]))
			strength[1]=len(list(collated['temp']['onice'][strength[1]]))
			play['changes'][changei]['Strength']=str(strength[0])+'v'+str(strength[1])
		if len(list(collated['temp']['toi'][play['dt']])) == 0:
			del(collated['temp']['toi'][play['dt']])
	
	return collated

def merge_pl_live_one(data, collated, playi, start=0):
	if 'LIVE' not in data:
		return collated
	return collated

def merge_pl_pxp_one(data, collated, playi, start=0):
	if 'PXP' not in data:
		return collated
	debug = False
	starti = 0
	endi = 0
	found = []

	play=collated['plays'][playi]
	if 'PXP' in play:
		return collated
	elif play['PLEvent'] == "ANTHEM":
		return collated
	elif play['PLEvent'] == "EGT":
		return collated
	elif play['PLEvent'] == "PGEND":
		return collated
	elif play['PLEvent'] == "PGSTR":
		return collated

	for i in range(0, len(data['PXP']['plays'])):
		pxplay=data['PXP']['plays'][i]

		if 'period' not in pxplay:
			continue

		if pxplay['period'] == 'SO':
			pxplay['period']=5
			data['PXP']['plays'][i]=pxplay

		if pxplay['period'] > int(play['Period']):
			starti=i
			break

		dt=decimaltime(pxplay['timeInPeriod'], pxplay['period'])
		if dt >= play['dt']:
			starti=i
			break

	for i in range(starti+1, len(data['PXP']['plays'])):
		endi=i
		pxplay=data['PXP']['plays'][i]

		if 'period' not in pxplay:
			continue
		if pxplay['period'] == 'SO':
			pxplay['period']=5
			data['PXP']['plays'][i]=pxplay
		if pxplay['period'] > int(play['Period']):
			break
		dt=decimaltime(pxplay['timeInPeriod'], pxplay['period'])
		if dt > play['dt']:
			break

	matches=[]
	for i in range(starti, endi):
		pxplay=data['PXP']['plays'][i]
		if 'PLPlay' in pxplay:
			continue
		#pxplay['details']['xCoord']
		#pxplay['details']['yCoord']
		#pxplay['details']['zoneCode']
		if pxplay['typeDescKey'] == 'blocked-shot':
			if play['PLEvent'] == 'BLOCK':
				matches.append(i)
				#pxplay['details']['shootingPlayerId']
				#pxplay['details']['blockingPlayerId']
				#pxplay['details']['reason']
		elif pxplay['typeDescKey'] == 'delayed-penalty':
			continue
			if play['PLEvent'] == 'PENL':
				matches.append(i)
		elif pxplay['typeDescKey'] == 'faceoff':
			if play['PLEvent'] == 'FAC':
				matches.append(i)
				#pxplay['details']['losingPlayerId']
				#pxplay['details']['winningPlayerId']
		elif pxplay['typeDescKey'] == 'game-end':
			if play['PLEvent'] == 'GEND':
				matches.append(i)
		elif pxplay['typeDescKey'] == 'giveaway':
			if play['PLEvent'] == 'GIVE':
				matches.append(i)
		elif pxplay['typeDescKey'] == 'goal':
			match=False
			if play['PLEvent'] == 'GOAL':
				if debug:
					print("   "+pxplay['typeDescKey']+" == "+play['PLEvent'])
				for nhlid in play['Shooter']:
					if pxplay['details']['scoringPlayerId'] == nhlid:
						if debug:
							print("   "+str(pxplay['details']['scoringPlayerId'])+" == "+str(nhlid))
						match=True
						break
					elif debug:
						print("   "+str(pxplay['details']['scoringPlayerId'])+" != "+str(nhlid))

				if match:
					match=False
					if 'Primary Assister' in play and 'assist1PlayerId' in pxplay['details']:
						for nhlid in play['Primary Assister']:
							if pxplay['details']['assist1PlayerId'] == nhlid:
								if debug:
									print("   "+str(pxplay['details']['assist1PlayerId'])+" == "+str(nhlid))
								match=True
								break
							elif debug:
								print("   "+str(pxplay['details']['assist1PlayerId'])+" != "+str(nhlid))
					elif 'Primary Assister' not in play and 'assist1PlayerId' not in pxplay['details']:
						match=True
					elif 'Primary Assister' in play and 'assist1PlayerId' not in pxplay['details']:
						if debug:
							print("   1st assist in play, but not pxp")
					elif 'Primary Assister' not in play and 'assist1PlayerId' in pxplay['details']:
						if debug:
							print("   1st assist in pxp, but not play")

				if match:
					match=False
					if 'Secondary Assister' in play and 'assist2PlayerId' in pxplay['details']:
						for nhlid in play['Secondary Assister']:
							if pxplay['details']['assist2PlayerId'] == nhlid:
								if debug:
									print("   "+str(pxplay['details']['assist2PlayerId'])+" == "+str(nhlid))
								match=True
								break
							elif debug:
								print("   "+str(pxplay['details']['assist2PlayerId'])+" != "+str(nhlid))
					elif 'Secondary Assister' not in play and 'assist2PlayerId' not in pxplay['details']:
						match=True
					elif 'Secondary Assister' in play and 'assist2PlayerId' not in pxplay['details']:
						if debug:
							print("   2nd assist in play, but not pxp")
					elif 'Secondary Assister' not in play and 'assist2PlayerId' in pxplay['details']:
						if debug:
							print("   2nd assist in pxp,but not play")
			elif debug:
				print("   "+pxplay['typeDescKey']+" != "+play['PLEvent'])

			if match:
				if debug:
					print("      Match!")
				matches.append(i)
			elif debug:
				print(json.dumps(pxplay, indent=3))
				print(json.dumps(play, indent=3))
				print("      No match")
				#pxplay['details']['goalieInNetId']
				#pxplay['details']['shotType']
		elif pxplay['typeDescKey'] == 'hit':
			if play['PLEvent'] == 'HIT':
				matches.append(i)
				#pxplay['details']['hittingPlayerId']
				#pxplay['details']['hitteePlayerId']
				#pxplay['details']['shotType']
		elif pxplay['typeDescKey'] == 'failed-shot-attempt':
			if play['PLEvent'] == 'MISS':
				matches.append(i)
				#pxplay['details']['shootingPlayerId']
				#pxplay['details']['goalieInNetId']
				#pxplay['details']['shotType']
				#pxplay['details']['reason']
		elif pxplay['typeDescKey'] == 'missed-shot':
			if play['PLEvent'] == 'MISS':
				matches.append(i)
				#pxplay['details']['shootingPlayerId']
				#pxplay['details']['goalieInNetId']
				#pxplay['details']['shotType']
				#pxplay['details']['reason']
		elif pxplay['typeDescKey'] == 'penalty':
			if play['PLEvent'] == 'PENL':
				matches.append(i)
				#pxplay['details']['committedByPlayerId']
				#pxplay['details']['drawnByPlayerId']
				#pxplay['details']['typeCode']
				#pxplay['details']['descKey']
				#pxplay['details']['duration']
		elif pxplay['typeDescKey'] == 'period-end':
			if play['PLEvent'] == 'PEND':
				matches.append(i)
		elif pxplay['typeDescKey'] == 'period-start':
			if play['PLEvent'] == 'PSTR':
				matches.append(i)
		elif pxplay['typeDescKey'] == 'shootout-complete':
			if play['PLEvent'] == 'SOC':
				matches.append(i)
		elif pxplay['typeDescKey'] == 'shot-on-goal':
			if play['PLEvent'] == 'SHOT':
				matches.append(i)
				#pxplay['details']['shootingPlayerId']
				#pxplay['details']['goalieInNetId']
				#pxplay['details']['shotType']
		elif pxplay['typeDescKey'] == 'stoppage':
			if play['PLEvent'] == 'STOP':
				matches.append(i)
				#pxplay['details']['reason']
		elif pxplay['typeDescKey'] == 'takeaway':
			if play['PLEvent'] == 'TAKE':
				matches.append(i)
				#pxplay['details']['playerId']
				#pxplay['details']['playerId']
		else:
			print("Unknown type: "+pxplay['typeDescKey'])
			print(json.dumps(pxplay, indent=3))
			sys.stdin.readline()
			exit(9)

	if len(matches) == 1:
		collated['plays'][playi]['PXP']=data['PXP']['plays'][matches[0]]
		data['PXP']['plays'][matches[0]]['PLPlay']=playi
	elif len(matches) > 1:
		for i in range(starti, endi):
			pxplay=data['PXP']['plays'][i]
			print(json.dumps(pxplay, indent=3))
		print(json.dumps(collated['plays'][playi], indent=3))
		

#	if play['PLEvent'] == 'GOAL':
#		print("Did this match?")
#		sys.stdin.readline()
	return collated
				

def merge_pl_live_one(data, collated, playi, start=0):
	if 'LIVE' not in data:
		return collated
	return collated
	debug = True
	starti = None
	endi = 0
	found = []
	if debug:
		print("------------------MERGE---------------------")
		print(json.dumps(play, indent=3))
	
	play=collated['plays'][playi]

	if 'LIVE' in play:
		return play

	if 'PLEvent' not in play:
		print(collated['gamePk'])
		print("No PL in play")
		exit(1)

	if play['PLEvent'] == 'ANTHEM':
		return play
	elif play['PLEvent'] == 'CHANGE':
		return play
	elif play['PLEvent'] == 'DELPEN':
		return play
	elif play['PLEvent'] == 'PGSTR':
		return play
	elif play['PLEvent'] == 'PEND':
		return play
		if liveplay['result']['event'] == 'Period Official':
			newplay={}
			newplay['Period']=liveplay['about']['period']
			newplay['Elapsed']=liveplay['about']['periodTime']
			newplay['Remaining']=liveplay['about']['periodTimeRemaining']
			newplay['dt'] = decimaltime(newplay['Elapsed'], newplay['Period'])
			collated['plays'].insert(playi+1, newplay)
			found=[playi+1]
	elif play['PLEvent'] == 'PGSTR':
		return play
	elif play['PLEvent'] == 'PGEND':
		return play
	elif play['PLEvent'] == 'PSTR':
		return play
		if liveplay['result']['event'] == 'Period Ready':
			newplay={}
			newplay['Period']=liveplay['about']['period']
			newplay['Elapsed']=liveplay['about']['periodTime']
			newplay['Remaining']=liveplay['about']['periodTimeRemaining']
			newplay['dt'] = decimaltime(newplay['Elapsed'], newplay['Period'])
			collated['plays'].insert(playi, newplay)
			found=[playi]

	for liveplayi in range(start, 0, -1):
		liveplay=data['LIVE']['liveData']['plays']['allPlays'][liveplayi]
		dt = decimaltime(liveplay['about']['periodTime'], liveplay['about']['period'])

		if dt < play['dt']:
			start=liveplayi
			break

	if debug:
		print("   Beginning at "+str(start))
	for liveplayi in range(start, len(data['LIVE']['liveData']['plays']['allPlays'])):
		liveplay=data['LIVE']['liveData']['plays']['allPlays'][liveplayi]
		dt = decimaltime(liveplay['about']['periodTime'], liveplay['about']['period'])

		if int(play['Period']) > int(liveplay['about']['period']):
			continue
		elif int(play['Period']) < int(liveplay['about']['period']):
			if debug:
				print("Out of period")
			endi=liveplayi
			break

		if int(play['dt']) > int(dt):
			continue
		elif int(play['dt']) < int(dt):
			if debug:
				print("   Out of dt: "+str(play['dt'])+" > "+str(dt))
			endi=liveplayi
			break

		if starti is None:
			starti = liveplayi

		endi=liveplayi
		if debug:
			print("   Looking at "+str(liveplayi))

		match=False
		if play['PLEvent'] == 'BLOCK':
			if liveplay['result']['event'] == 'Blocked Shot':
				match=True
			else:
				print(liveplay['result']['event']+" != 'Blocked Shot'")
		elif play['PLEvent'] == 'CHL':
			if liveplay['result']['event'] == 'Official Challenge':
				match=True
		elif play['PLEvent'] == 'EISTR':
			if liveplay['result']['event'] == 'Early Intermission Start':
				match=True
		elif play['PLEvent'] == 'EIEND':
			if liveplay['result']['event'] == 'Early Intermission End':
				match=True
		elif play['PLEvent'] == 'EGT':
			if liveplay['result']['event'] == 'Emergency Goaltender':
				match=True
		elif play['PLEvent'] == 'FAC':
			if liveplay['result']['event'] == 'Faceoff':
				match=True
		elif play['PLEvent'] == 'GEND':
			if liveplay['result']['event'] == 'Game End':
				match=True
		elif play['PLEvent'] == 'GIVE':
			if liveplay['result']['event'] == 'Giveaway':
				match=True
		elif play['PLEvent'] == 'GOAL':
			if liveplay['result']['event'] == 'Goal':
				match=True
		elif play['PLEvent'] == 'GOFF':
			if liveplay['result']['event'] == 'Game Official':
				match=True
		elif play['PLEvent'] == 'HIT':
			if liveplay['result']['event'] == 'Hit':
				match=True
		elif play['PLEvent'] == 'MISS':
			if liveplay['result']['event'] == 'Missed Shot':
				match=True
			elif liveplay['result']['event'] == 'Failed Shot Attempt':
				match=True
		elif play['PLEvent'] == 'PENL':
			if liveplay['result']['event'] == 'Penalty':
				if re.search('[(]'+str(liveplay['result']['penaltyMinutes'])+' min[)]', play['PL']['Description'] ):
					if re.search('Unsportsmanlike conduct', play['PL']['Description']):
						if liveplay['result']['secondaryType'] == 'Unsportsmanlike conduct':
							match=True
						elif re.search('[Uu]nsportsmanlike[ \t\n\r\f\v]+[Cc]onduct', liveplay['result']['description']):
							match=True
					else:
						if liveplay['result']['secondaryType'] == 'Unsportsmanlike conduct':
							pass
						elif re.search('[Uu]nsportsmanlike[ \t\n\r\f\v]+[Cc]onduct', liveplay['result']['description']):
							pass
						else:
							match=True
		elif play['PLEvent'] == 'SOC':
			if liveplay['result']['event'] == 'Shootout Complete':
				match=True
		elif play['PLEvent'] == 'SHOT':
			if liveplay['result']['event'] == 'Shot':
				match=True
		elif play['PLEvent'] == 'STOP':
			if liveplay['result']['event'] == 'Stoppage':
				if liveplay['result']['description'] == 'Goalie Puck Frozen Played Beyond Center Line':
					if re.search('PUCK FRZN[-]GOALIE[-]BYND CTR', play['PL']['Description']):
						match=True
				elif re.search(liveplay['result']['description'].upper(), play['PL']['Description']):
					match=True
				elif re.search('Missing key', liveplay['result']['description']):
					match=True
			elif liveplay['result']['eventTypeId'] == 'CHALLENGE':
				if re.search('^[ \t\n\r\f\v]*CHLG', play['PL']['Description']):
					match=True
		elif play['PLEvent'] == 'TAKE':
			if liveplay['result']['event'] == 'Takeaway':
				match=True
		else:
			print("No plan for "+play['PLEvent']+"/"+liveplay['result']['event'])
			sys.stdin.readline()

		if debug and not match:
			print("   "+play['PLEvent']+" != "+liveplay['result']['event'])

		if match:
			if 'Shot Type' in play and liveplay['result']['secondaryType'] in liveplay:
				match=False
				if play['Shot Type'] == 'Slap':
					if liveplay['result']['secondaryType'] == 'Slap Shot':
						match=True
				elif play['Shot Type'] == 'Wrist':
					if liveplay['result']['secondaryType'] == 'Wrist Shot':
						match=True
				elif play['Shot Type'] == 'Snap':
					if liveplay['result']['secondaryType'] == 'Snap Shot':
						match=True
				elif play['Shot Type'] == 'Failed Attempt':
					if liveplay['result']['event'] == 'Failed Shot Attempt':
						match=True
				if debug:
					if not match:
						print("   "+play['Shot Type']+" != "+liveplay['result']['secondaryType'])
					else:
						print("   "+play['Shot Type']+" == "+liveplay['result']['secondaryType'])

		if match:
			if 'Distance' in play and 'coordinates' in liveplay and 'x' in liveplay['coordinates'] and 'y' in liveplay['coordinates']:
				match=False
				pxs=(90-liveplay['coordinates']['x'])**2
				nxs=(-90-liveplay['coordinates']['x'])**2
				ys=(0-liveplay['coordinates']['y'])**2
				pd=math.sqrt(pxs+ys)
				nd=math.sqrt(nxs+ys)
				r = int(re.sub('[^0-9]+', '', play['Distance']))
				if ((pd-r) > -2 and (pd-r) < 2) or ((nd-r) > -2 and (nd-r) < 2):
					if debug:
						print("   Distance r of ("+str(liveplay['coordinates']['x'])+","+str(liveplay['coordinates']['y'])+") -> "+str(int(pd*1000)/1000)+" / "+str(int(nd*1000)/1000)+" < |"+str(int(r*1000)/1000)+"|")
					match=True
				else:
					if debug:
						print("   Distance r of ("+str(liveplay['coordinates']['x'])+","+str(liveplay['coordinates']['y'])+") -> "+str(int(pd*1000)/1000)+" / "+str(int(nd*1000)/1000)+" <> |"+str(int(r*1000)/1000)+"|")
					match=False

		if match:
			if debug:
				print("   Type specific matches")
			if 'players' in liveplay:
				for player in liveplay['players']:
					type=player['playerType']
					if type in play:
						match=False
						for plplayer in play[type]:
							if player['player']['id'] == plplayer:
								match=True
								break
							elif plplayer == 'bench':
								match=True
								break
							elif debug:
								print("   "+type+": "+str(player['player']['id'])+" != "+str(plplayer))
						if match:
							if debug:
								print("   Player: "+type+": "+str(player['player']['id'])+" == "+str(plplayer))
						else:
							if debug:
								print("   Player: "+type+": "+str(player['player']['id'])+" has no match")

		if match:
			found.append(liveplayi)

	if starti is None:
		starti=endi-1

	if debug:
		print("   Ending at "+str(liveplayi)+" with "+str(len(found))+" results")

	if len(found) == 1:
		liveplay=data['LIVE']['liveData']['plays']['allPlays'][found[0]]
		play['LIVE']=liveplay
		play['LIVEEvent']=liveplay['result']['event']
		play['LIVEi']=liveplayi
		if debug:
			print(json.dumps(liveplay, indent=3))
	elif len(found) > 1:
		liveplay=data['LIVE']['liveData']['plays']['allPlays'][found[0]]
		play['LIVE']=liveplay
		play['LIVEEvent']=liveplay['result']['event']
		play['LIVEi']=liveplayi
		play['LIVEalso']=[]

		for foundi in found:
			if debug:
				print(json.dumps(data['LIVE']['liveData']['plays']['allPlays'][foundi], indent=3))
			play['LIVEalso'].append(data['LIVE']['liveData']['plays']['allPlays'][foundi])

	elif len(found) == 0:
		for i in range(starti, endi):
			liveplay=data['LIVE']['liveData']['plays']['allPlays'][i]
			print(json.dumps(liveplay, indent=3))
		print(json.dumps(play, indent=3))
		print(collated['gamePk'])
		print("No matches")
		exit(2)

	return play

def undectime(time):
	s=int(time) % 60
	m=int((time-s)/60)
	p = int(m/20)+1
	m=m % 20

	return "{p} {m:02}:{s:02}".format(p=p, m=m, s=s)

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
	
	if str(period) == "SO":
		period=5

	if period != 0:
		period=float(period)
		t = t + (period/100.0)
		t = t + (period-1)*1200

	return t

def get_game_components(game):
	gameid=str(game['gamePk'])
	season=gameid[0:4]
	type=gameid[4:6]
	gamenum=gameid[6:]

	return [season, type, gamenum]

def get_game_prefix():
	gamedir=os.getcwd()
	return gamedir

def get_game_path(game):
	[season, type, gamenum]=get_game_components(game)

	gamedir=get_game_prefix()+os.sep+str(season)+os.sep+str(type)
	os.makedirs(name=gamedir, exist_ok=True)
	gamepath=gamedir+os.sep+str(gamenum)

	return gamepath

def process_game(game):
	[season, type, gamenum]=get_game_components(game)

	gamepath=get_game_path(game)

	data=get_gamedata(game)
	newdata=None
	if data is not None:
		print("Collating game: "+str(season)+"/"+str(type)+"/"+str(gamenum))
		newdata=collate(data)

	if newdata is not None:
		newdata['version']=1

		try:
			if len(data['PL']) > 0 and (data['PL'][-1]['Event'] == "GEND" or data['PL'][-1]['Event'] == "GOFF" or data['PL'][-1]['Event'] == "EGPID"):
				newdata['status']="Final"
			else:
				newdata['status']="Ongoing"
		except KeyError as e:
			pass

		try:
			if (data['PXP']['gameState'] == 'FINAL' or data['PXP']['gameState'] == 'OFF') and data['PXP']['gameScheduleState'] == 'OK':
				print("Final by gameState")
				if 'status' in newdata and newdata['status'] == 'Ongoing':
					print(str(data['PXP']['gameState'])+" == OFF/FINAL")
					print(str(data['PXP']['gameScheduleState'])+" == OK")
					if len(data['PL']) > 0:
						print(str(data['PL'][-1]['Event'])+" == GEND/GOFF")
					print(str(data['PXP']['plays'][-1]['typeDescKey'])+" == shootout-complete/game-end")
					if len(data['PXP']['plays']) > 0:
						print(str(data['PXP']['plays'][-1]['typeCode'])+" == 523, 524, 527")
					print(str(data['PXP']['clock']['running'])+" == false")
					print(str(data['PXP']['clock']['inIntermission'])+" == false")
					print("Game: "+str(newdata['GAME']['gamePk']))
					#exit(5)
				newdata['status']="Final"
			else:
				print("Not final by gameState")
				if 'status' in newdata and newdata['status'] == 'Final':
					print(str(data['PXP']['gameState'])+" == OFF/FINAL")
					print(str(data['PXP']['gameScheduleState'])+" == OK")
					print(str(data['PL'][-1]['Event'])+" == GEND/GOFF")
					print(str(data['PXP']['plays'][-1]['typeDescKey'])+" == shootout-complete/game-end")
					print(str(data['PXP']['plays'][-1]['typeCode'])+" == 523, 524, 527")
					print(str(data['PXP']['clock']['running'])+" == false")
					print(str(data['PXP']['clock']['inIntermission'])+" == false")
					print("Game: "+str(newdata['GAME']['gamePk']))
					exit(5)
				newdata['status']="Ongoing"

			if len(data['PXP']['plays']) > 0 and (data['PXP']['plays'][-1]['typeDescKey'] == 'game-end' or data['PXP']['plays'][-1]['typeDescKey'] == 'shootout-complete'):
				print("Final by last play typeDescKey")
				if 'status' in newdata and newdata['status'] == 'Ongoing':
					print(str(data['PXP']['gameState'])+" == OFF/FINAL")
					print(str(data['PXP']['gameScheduleState'])+" == OK")
					print(str(data['PL'][-1]['Event'])+" == GEND/GOFF")
					print(str(data['PXP']['plays'][-1]['typeDescKey'])+" == shootout-complete/game-end")
					print(str(data['PXP']['plays'][-1]['typeCode'])+" == 523, 524, 527")
					print(str(data['PXP']['clock']['running'])+" == false")
					print(str(data['PXP']['clock']['inIntermission'])+" == false")
					print("Game: "+str(newdata['GAME']['gamePk']))
					#exit(5)
				newdata['status']="Final"
			else:
				print("Not final by typeDescKey")
				if 'status' in newdata and newdata['status'] == 'Final':
					print(str(data['PXP']['gameState'])+" == OFF/FINAL")
					print(str(data['PXP']['gameScheduleState'])+" == OK")
					print(str(data['PL'][-1]['Event'])+" == GEND/GOFF")
					print(str(data['PXP']['plays'][-1]['typeDescKey'])+" == shootout-complete/game-end")
					print(str(data['PXP']['plays'][-1]['typeCode'])+" == 523, 524, 527")
					print(str(data['PXP']['clock']['running'])+" == false")
					print(str(data['PXP']['clock']['inIntermission'])+" == false")
					print("Game: "+str(newdata['GAME']['gamePk']))
					#exit(5)
				newdata['status']="Ongoing"

			if len(data['PXP']['plays']) > 0 and (data['PXP']['plays'][-1]['typeCode'] == 523 or data['PXP']['plays'][-1]['typeCode'] == 524 or data['PXP']['plays'][-1]['typeCode'] == 527):
				print("Final by last play typeCode")
				if 'status' in newdata and newdata['status'] == 'Ongoing':
					print(str(data['PXP']['gameState'])+" == OFF/FINAL")
					print(str(data['PXP']['gameScheduleState'])+" == OK")
					print(str(data['PL'][-1]['Event'])+" == GEND/GOFF")
					print(str(data['PXP']['plays'][-1]['typeDescKey'])+" == shootout-complete/game-end")
					print(str(data['PXP']['plays'][-1]['typeCode'])+" == 523, 524, 527")
					print(str(data['PXP']['clock']['running'])+" == false")
					print(str(data['PXP']['clock']['inIntermission'])+" == false")
					print("Game: "+str(newdata['GAME']['gamePk']))
					exit(5)
				newdata['status']="Final"
			else:
				print("Not final by typeCode")
				if 'status' in newdata and newdata['status'] == 'Final':
					print(str(data['PXP']['gameState'])+" == OFF/FINAL")
					print(str(data['PXP']['gameScheduleState'])+" == OK")
					print(str(data['PL'][-1]['Event'])+" == GEND/GOFF")
					print(str(data['PXP']['plays'][-1]['typeDescKey'])+" == shootout-complete/game-end")
					print(str(data['PXP']['plays'][-1]['typeCode'])+" == 523, 524, 527")
					print(str(data['PXP']['clock']['running'])+" == false")
					print(str(data['PXP']['clock']['inIntermission'])+" == false")
					print("Game: "+str(newdata['GAME']['gamePk']))
					exit(5)
				newdata['status']="Ongoing"

			print(json.dumps(data['PXP']['clock'], indent=3))
#			if data['PXP']['clock']['secondsRemaining'] == 0 and data['PXP']['clock']['running'] == False and data['PXP']['clock']['inIntermission'] == False:
#				print("Final by clock")
#				if 'status' in newdata and newdata['status'] == 'Ongoing':
#					exit(5)
#				newdata['status']="Final"
#			else:
#				print("Not final by clock")
#				if 'status' in newdata and newdata['status'] == 'Final':
#				newdata['status']="Ongoing"

			newdata['status']="Ongoing"
			for note in newdata['notes']:
				if note['Event'] == 'FINAL':
					print("Final by PL note")
					newdata['status']="Final"
					break

		except KeyError as e:
			print(e)
			pass

		print("Writing game: "+str(season)+"/"+str(type)+"/"+str(gamenum))
		f=open(gamepath, 'w')
		f.write(json.dumps(newdata))
		f.close()
	else:
		wipe_game_cache(game)
		print("Writing failure: "+str(season)+"/"+str(type)+"/"+str(gamenum))
		f=open(gamepath+"-failed", 'w')
		f.write(json.dumps(data))
		f.close()

def wipe_game_cache(game):
	if 'html' not in game:
		gameid=str(game['gamePk'])
		game['html']={}
		game['html']['y']=gameid[0:4]
		game['html']['t']=gameid[4:6]
		game['html']['n']=gameid[6:]
	urls=[]

	#Old HTML reports
	for htmtype in ['RO', 'PL', 'TH', 'TV', 'GS', 'SO']:
		urls.append('http://www.nhl.com/scores/htmlreports/'+str(game['season'])+'/'+htmtype+game['html']['t']+game['html']['n']+'.HTM')
	
	#Livedata
	urls.append('https://statsapi.web.nhl.com/api/v1/game/'+str(game['gamePk'])+'/feed/live?site=en_nhl')

	#Apiweb
	for suffix in ['play-by-play', 'landing', 'boxscore']:
		urls.append('https://api-web.nhle.com/v1/gamecenter/'+str(game['gamePk'])+'/'+suffix)

	for url in urls:
		cachefile = cachename(url)
		try:
			f=open(cachefile, 'r')
			f.close()
			os.unlink(cachefile)
		except FileNotFoundError as e:
			pass
#		except KeyError as e:
#			pass
		except Exception as e:
			print(e)
			exit(11)

def final_game(game):
	gamepath=get_game_path(game)
	game={}
	try:
		os.unlink(gamepath+"-failed")
		return False
	except Exception as e:
		pass

	try:
		f=open(gamepath, 'r')
		gamedoc=''.join(f.readlines())
		game=json.loads(gamedoc)
		f.close()
	except FileNotFoundError as e:
		print(e)
		pass
	except Exception as e:
		print(e)
		pass

	try:
		if False and game['status'] == 'Final' and game['version'] == 1:
			return True
	except KeyError as e:
		print(e)
		pass
	except Exception as e:
		print(e)
		pass

	return False

def make_game_struct(gamepk):
	game={}
	game['gamePk']=str(gamepk)
	game['path']=game['gamePk'][0:4]+'/'+game['gamePk'][4:6]+'/'+game['gamePk'][6:10]
	game['season']=game['gamePk'][0:4]
	game['season']=str(game['season'])+str(int(game['season'])+1)
	game['gameType']="P"
	game['link']='/api/v1/game/'+game['gamePk']+'/feed/live'
	return game


def recover():
	gamedir=get_game_prefix()
	for year in os.listdir(gamedir):
		yeardir=gamedir+os.sep+str(year)
		if not os.path.isdir(yeardir):
			continue
		print(year)
		for seasontype in os.listdir(yeardir):
			typedir=yeardir+os.sep+str(seasontype)
			if not os.path.isdir(typedir):
				continue
			print('   '+seasontype)
			for num in os.listdir(typedir):
				numfile=typedir+os.sep+str(num)
				if not os.path.isfile(numfile):
					continue
				print('      '+num)
				game=make_game_struct(str(year)+str(seasontype)+str(num))
				if not final_game(game):
					wipe_game_cache(game)
					process_game(game)

def thread_main(game):
	print("Game: "+str(game['gamePk']))

#	if 'home' in game and 'away' in game and game['home'] != 'MTL' and game['away'] != 'MTL':
#		print("Skipping "+str(game['gamePk'])+" because of Montreal")

	if not final_game(game):
		wipe_game_cache(game)
		process_game(game)
	else:
		print("Skipping "+str(game['gamePk']))

def get_season(season):
	games=[]
	start=int(season)
	end=int(season)
	if start > 10000:
		start=int(start/10000)
		end=start
	end=end+1
	season=(start*10000)+end

	start=datetime.datetime(start, 7, 1)
	end=datetime.datetime(end, 10, 1)
	now=datetime.datetime.today()
	if end > now:
		end=now

	day=datetime.timedelta(days=1)
	while start <= end:
		datestr=start.strftime('%Y-%m-%d')
		dategames=get_schedule(datestr)
		for game in dategames:
			if int(game['season']) == int(season):
				games.append(game)
		start=start+day
	return games

def main():
	games=[]
	single_thread=True
	if len(sys.argv) > 1:
		for i in range(1, len(sys.argv)):
			if re.match('[0-9]+[/][0-9]+[/][0-9]+', sys.argv[i]):
				gamepk=sys.argv[i]
				season=re.sub('[/].*$', '', gamepk)
				type=re.sub('^[^/]*[/]', '', gamepk)
				type=re.sub('[/].*$', '', type)
				gamenum=re.sub('^.*[/]', '', gamepk)
				gamepk = season[0:4]
				gamepk = gamepk + type
				gamepk = gamepk + gamenum
				game=make_game_struct(gamepk)
				games.append(game)
			elif re.search('^[0-9][0-9][0-9][0-9]$', sys.argv[i]):
				games=get_season(sys.argv[i])
			elif re.search('^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$', sys.argv[i]):
				games=get_season(sys.argv[i])
			elif re.search('^[0-9][0-9][0-9][0-9]0[0-9][0-9][0-9][0-9][0-9]$', sys.argv[i]):
				games.append(make_game_struct(sys.argv[i]))
			elif sys.argv[i] == "-1":
				single_thread=True

	else:
		day=datetime.timedelta(days=1)
		now=datetime.datetime.today()
		then=datetime.datetime(2019, 7, 12)
		while now >= then:
			datestr=now.strftime('%Y-%m-%d')
			for game in get_schedule(datestr, datestr):
				games.append(game)
			now=now-day

	if single_thread or len(games) == 1:
		for game in games:
			thread_main(game)
	else:
		with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
			executor.map(thread_main, games)

main()
