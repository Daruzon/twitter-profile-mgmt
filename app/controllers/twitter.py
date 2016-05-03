#!/usr/bin/env python3
# coding: utf-8
# enable debugging

import os, sys, requests, time
from datetime import datetime, date
from math import fabs
from collections import OrderedDict

if 'CONFPATH' not in os.environ.keys():
	os.environ['CONFPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"/includes/config"
sys.path.append( os.environ['CONFPATH'] )
import config
config.set_incpath()

if config.isweb():
	import request
else:
	import command

import output, mongo, session, tweepy
DB = mongo.db("twitter")

login = False
signup = False
me = None
auth = None
TwitterAPI = None

from requests_oauthlib import OAuth1Session

consumer_key = config.config['twitter']['key']
consumer_secret = config.config['twitter']['secret']
_last_cursor_ = {'followers':{}, 'influencers':{}, 'newcomers':{}, 'quitters':{}}

def authorize(consumer_key, consumer_secret):
	callbackuri = request.protocol+'://'+request.host+'/twitter/callback/'
	oauth_client = OAuth1Session(consumer_key, client_secret=consumer_secret, callback_uri=callbackuri)

	print('Requesting temp token from Twitter')

	try:
		resp = oauth_client.fetch_request_token('https://api.twitter.com/oauth/request_token')
	except ValueError as e:
		print('Invalid response from Twitter requesting temp token: %s' % e)
		return False
	url = oauth_client.authorization_url('https://api.twitter.com/oauth/authorize')+'&oauth_callback='+callbackuri
	request_token = resp.get('oauth_token')
	request_token_secret = resp.get('oauth_token_secret')
	
	return (url, request_token, request_token_secret)


def get_access_token(consumer_key=consumer_key, consumer_secret=consumer_secret, request_token=None, request_token_secret=None, request_verifier=None):
	if request_token == None:
		request_token = session.SESSION['request_token']
	if request_token_secret == None:
		request_token_secret = session.SESSION['request_token_secret']
	if request_verifier == None:
		request_verifier = request.params['oauth_verifier']
	
	oauth_client = OAuth1Session(consumer_key, client_secret=consumer_secret,
								 resource_owner_key=request_token,
								 resource_owner_secret=request_token_secret,
								 verifier=request_verifier
	)
	try:
		resp = oauth_client.fetch_access_token('https://api.twitter.com/oauth/access_token')
	except ValueError as e:
		print('Invalid response from Twitter requesting access token: %s' % e)
		return
	
	access_token = resp.get('oauth_token')
	access_token_secret = resp.get('oauth_token_secret')
	return (access_token, access_token_secret)
	currentuser = user(name="_mdacruz")


class user:
	
	def __init__(self, id=None, name=None, data=None):
		if not isinstance(data, dict):
			if name != None:
				data = self.loadFromName(name)
			elif id != None:
				data = self.loadFromID(id, data=data)
			else:
				data = self.loadFromID(data=data)
		
		self.started = False
		self.data = {}
		for d in data:
			setattr(self, d, data[d])
		self.started = True
	
	def __getattr__(self, attr):
		if attr not in ['data', 'started']:
			if attr in self.data.keys():
				return self.data[attr]
			else:
				return None
	
	def __setattr__(self, attr, value):
		if attr not in ['data', 'started']:
			self.data[attr] = value
			if self.started:
				DB.users.update(
					{'id':self.id },
					{'$set':{attr:value}, '$currentDate': {'last_update': True}
				})
		else:
			self.__dict__[attr] = value
	
	def __delattr__(self, attr):
		del self.__dict__[attr]
		if attr not in ['data', 'started']:
			if self.started:
				DB.users.update(
					{'id':self.id },
					{'$unset':{attr:True}, '$currentDate': {'last_update': True}
				})	
	
	# On charge l'utilisateur depuis la BDD (par son ID)
	def loadFromID(self, id=None, data=None):
		if id == None:
			id = get_user()['id']
		
		user = DB.users.find_one({'id':id})
		if user != None:
			return user
		else:
			if data == None:
				data = get_user(user_id=id)
				data['sortable_username'] = data['name'].lower()
			if data['url'] != None:
				url = self.updateTwitterUrl(url=data['url'], update=False)
				if url != None:
					data['url'] = url
			
			#if 'status' in data.keys():
			#	del data['status']
			#if 'entities' in data.keys():
			#	del data['entities']
			
			DB.users.insert_one(data)
			user = DB.users.find_one({'id':id})
			return user
			
	# On charge l'utilisateur depuis la BDD (par son nom)
	def loadFromName(self, name):
		user = DB.users.find_one({'screen_name':name})
		if len(user):
			return user
		else:
			print("User not found")
	
	def can_query(self, request):
		entry = DB.accounts.find_one({'id':self.id})
		if 'limits' in entry.keys():
			return bool(entry['limits'][request]['remaining']-2)
		else:
			self.retrieve_api_limits()
			return True
		
	def retrieve_api_limits(self):
		limits = TwitterAPI.rate_limit_status()['resources']
		l = {}
		for k, v in limits.items():
			for _k_, _v_ in v.items():
				l[_k_[1:].replace('/', '|')] = _v_
		
		DB.accounts.update({'id':self.id}, {'$set':{'limits': l}})
	
	def update_query_limit(self, request, minus=1):
		DB.accounts.update({'id':self.id}, {'$inc':{'limits.'+request+'.remaining': -minus}})
	
	def generate_metrics_entry(self):
		
		# On récupère les followers et influencers
		entries = OrderedDict()
		entries['followers'] 	=	list(get_followers(user_id=self.id))
		entries['influencers']	=	list(get_influencers(user_id=self.id))
		
		
		for cat in ['followers', 'influencers']:
			if isinstance(entries[cat], tuple):
				entries[cat] = entries[cat][0].values()
		
		# On cherche si la fiche a été analysée aujourd'hui
		todays_metrics = DB.metrics.find_one({'id': self.id, 'day':str(date.today())})
		
		# S'il y a bien une ligne, on en récupère les entrées déjà traitées
		if todays_metrics != None:
			#for i in entries.keys():
			#	if i in todays_metrics.keys():
			#		if 'list' in todays_metrics[i].keys():
			#			_fetched_ = DB.users.find({'id':{'$in':todays_metrics[i]['list']}})
			#			for u in _fetched_:
			#				entries[i].append(u)
			
			if 'followers' not in todays_metrics.keys() or 'cursor' not in todays_metrics['followers'].keys():
				yesterday = DB.metrics.find({"id":self.id, 'followers':{'$exists':True}, 'day':{'$ne':str(date.today())}}).sort('day', mongo.DESC)
				if yesterday != None and yesterday.count():
					yesterday = yesterday[0]
					entries['quitters'] = list(DB.users.find({'id':{ '$in': [x for x in set(yesterday['followers']['list']) - set([y['id'] for y in entries['followers']]) ]}}))
					entries['newcomers'] = list(DB.users.find({'id':{'$in':[x for x in set([y['id'] for y in entries['followers']]) - set(yesterday['followers']['list']) ]}}))
			
					for cat in ['newcomers', 'quitters']:
						if isinstance(entries[cat], tuple):
							entries[cat] = entries[cat][0].values()
		
		# Tant pour les entrées "followers" que "influenceurs", "newcomers" et "quitters"
		for categories in entries:
			if not len(entries[categories]):
				continue
			
			#print(type(entries[categories]), entries[categories], len(entries[categories]))
			
			_per_lang_ = {}
			_followers_ = []
			_following_ = []
			_tweets_ = []
			_ratios_tweets_ = []
			_ratios_follows_ = []
			_ids_ = []
			
			for _v_ in entries[categories]:
				if _v_ == []:
					continue
				
				if not isinstance(_v_, dict):
					_id_ = _v_
					_v_ = DB.users.find_one({'id':_id_})
				
				#print(type(_v_), _v_)
					
				_v_['lang'] = _v_['lang'][0:2]
				#url = self.updateTwitterUrl(_v_['url'], update=False)
				#if url != None:
				#	_v_['url'] = url
				
				#if 'status' in _v_.keys():
				#	del _v_['status']
				#if 'entities' in _v_.keys():
				#	del _v_['entities']
				
				_v_['sortable_username'] = _v_['name'].lower()
				DB.users.update_one(
					{'id': _v_['id']},
					{
						'$set': _v_, '$currentDate': {'last_update': True}
					},
					upsert=True
				)
				
				if _v_['lang'] not in _per_lang_.keys():
					_per_lang_[_v_['lang']] = 0
				_per_lang_[_v_['lang']] += 1
				_ids_.append(_v_['id'])
				_followers_.append(_v_['followers_count'])
				_following_.append(_v_['friends_count'])
				_tweets_.append(_v_['statuses_count'])
				
				if _v_['statuses_count'] != 0:
					_ratios_tweets_.append(_v_['followers_count']/_v_['statuses_count'])
				
				if _v_['friends_count'] != 0:
					_ratios_follows_.append(_v_['followers_count']/_v_['friends_count'])
			
			_followers_.sort()
			_following_.sort()
			
			if not len(_followers_) and not len(_following_):
				return False
			
			if len(_followers_)%2:
				if len(_followers_) == 1:
					_med_followers_ = _followers_[0]
				else:
					_med_followers_ = _followers_[int((len(_followers_)-1)/2)]
			else:
				_qm = _followers_[int((len(_followers_)-2)/2)]
				_qp = _followers_[int(len(_followers_)/2)]
				_med_followers_ = int(_qm + (_qp - _qm) / 2)
			
			if len(_following_)%2:
				if len(_following_) == 1:
					_med_following_ = _following_[0]
				else:
					_med_following_ = _following_[int((len(_following_)-1)/2)]
			else:
				_qm = _following_[int((len(_following_)-2)/2)]
				_qp = _following_[int(len(_following_)/2)]
				_med_following_ = int(_qm + (_qp - _qm) / 2)
			
			_update_tree_ = {
				'$set': {
					categories: {
						'list':_ids_,
						'number':len(_ids_),
						'languages':_per_lang_,
						'avg_followers':sum(_followers_)/len(_followers_),
						'avg_influencers':sum(_following_)/len(_following_),
						'med_followers':_med_followers_,
						'med_influencers':_med_following_,
						'avg_tweets':sum(_tweets_)/len(_tweets_),
						'ratio_impact':sum(_ratios_tweets_)/len(_ratios_tweets_),
						'ratio_influence':sum(_ratios_follows_)/len(_ratios_follows_),
					}
				},
				'$currentDate': {'time': True}
			}
			
			#if self.id in _last_cursor_[categories].keys():
			#	_update_tree_['$set'][categories]['cursor'] = _last_cursor_[categories][self.id]
			
			DB.metrics.update_one(
				{'id': self.id, 'day':str(date.today())},
				_update_tree_,
				upsert=True
			)
	
	
	def sendDM(self, screen_name=None, id=None, user=None):
		return True
	
	# Remplacer les URL en t.co par les vraies URL
	def updateTwitterUrl(self, url=None, update=True):
		u = url if url != None else self.url
				
		# On charge l'URL en t.co et on ne se laisse pas rediriger
		r = requests.get(u, allow_redirects=False)
		
		if 'location' not in r.headers.keys():
			return None
		
		# On enregistre l'URL vers laquelle Twitter veut nous rediriger
		if update:
			self.url = r.headers['location']
		else:
			return r.headers['location']
	
	
	# Récupérer le rang Alexa d'une URL d'utilisateur Twitter
	def getAlexaRank(self):
		
		# Si c'est une URL en t.co on la remplace par la vraie
		if '/t.co/' in self.url:
			oldurl = self.url
			self.updateTwitterUrl()
		
		# Ensuite on récupère la mini-page du module Chrome indiquant le rang Alexa, plutôt que d'utiliser l'API, qui est payante. 8-)
		r = requests.get('http://www.alexa.com/minisiteinfo/'+self.url).text
		
		# On découpe cette mini-page, on y localise où est écrit le numéro (qui contient des chiffres de 0 à 9 et des virgules), et on l'extrait
		pattern = '/> ([0-9,]*)</a>'
		details = re.search(pattern, r, re.I | re.S)
		nombre = details.group(1).replace(',', '').strip()
		
		# Si on a bien trouvé un nombre, on le renvoie
		if nombre.isdigit():
			return int(nombre)
			
		# Sinon on indique qu'on n'a pas trouvé
		else:
			return False
	
	def getWikiURL(self):
		options = {}
		for l in list(set(['en', 'fr', self.lang])):
			wording = self.name
			u = "https://"+l+".wikipedia.org/w/api.php?action=opensearch&format=json&formatversion=2&namespace=0&limit=10&suggest=true&search="+wording
			search = requests.get(u, allow_redirects=True)
			found = search.json()
			print(found)
			if not len(found[1]) or not len(found[1][0]):
				continue
			found.pop(0)
			results = [(found[0][i], found[1][i], found[2][i]) for i in range(0,len(found[0]))]
			if len(results):
				if len(results[0][0]) - len(self.name) in [-1, 1]:
					continue
					
				options[l] = {'name':results[0][0], 'description':results[0][1], 'url':results[0][2]}
				break
				
		return options
	
	
	def getLinkedInURL(self):
		wording  = self.name.split(' ')
		if len(wording) != 2:
			return ''
		
		u = "https://www.linkedin.com/pub/dir/?search=Rechercher&first="+wording[0]+"&last="+wording[1]
		search = requests.get(u, allow_redirects=False)
		
		if 'location' not in search.headers.keys():
			return None
		
		return r.headers['location']
				
	
	def shouldUnfollow(self):
		trouve = False
		for word in recherche:
			if word in self.description:
				trouve = True
		
		willUnfollow = not trouve
		
		if self.followers_count < 100:
			ratio = -1
		elif self.followers_count < 500:
			ratio = 1/2
		elif self.followers_count < 2000:
			ratio = 2/3
		else:
			ratio = 1
		
		if min(self.getFollowRatio(), self.getTweetRatio()) > ratio or max(self.getFollowRatio(), self.getTweetRatio()) > min(ratio * 3, 2):
			willUnfollow = True
		
		if self.lang in ['ar', 'ko', 'id', 'ja', 'ru', 'th']:
			willUnfollow = True
	
	
	def unfollow(self):
		updates = {
			'$set':{'unfollowing_since':datetime.now(), 'following':False},
			'$unset':{'following_since':1}
		}
		"""
		db::get("twitter")->users->update(['id'=>$user_id], $updates);
	
		$requete = ['user_id'=>$user_id];
		$user = (array)$cb->friendships_destroy($requete);
		$desabonnements++;
		$unfollowed[] = "@".$user_infos['screen_name'];
		//echo "\r[".date("H:i:s")."] [Désabonnement] [".$user_infos['screen_name']."] Encore $remaining requêtes.		  ";
		if($desabonnements >= $counter_unfollow)
			break;
		"""
		return True
		
	def whitelist(self):
		updates = {'$set':{'to_keep':True}}
		#db::get("twitter")->users->update(['id'=>$user_id], $updates);
		return False
	
	
	
	def unfollowBack(self, count=5):
		# Get current followers on Twitter
		updatedlist = []
		# Get past followers list on MongoDB
		pastlist = []
		
		for u in pastlist:
			# If a user unfollowed me
			if pastlist[u]['id'] not in updatedlist:
				
				# And if I was following him
				
					# Remove from MongoDB
					self.unfollow()
					#Send a bye-bye message
				
					count -= 1
	
	
	def shouldFollow():
		ratio_following = self.getFollowRatio()
		ratio_tweeting = self.getTweetRatio()
		
		if self.data['followers_count'] < 100:
			return False
		
		if self.data['verified']:
			return True
		
		trouve = False
		for word in recherches:
			if word in self.data['description']:
				trouve = True
		
		return trouve
	
	
		
	def follow(self):
		# On fait la mise à jour MongoDB
		DB.users.update(
			{'id':self.id },
			{'$set':{'following':True,'following_since':datetime.now()}, '$currentDate': {'last_update': True}
		})
		
		# On fait la requête à Twitter
		requete = {'user_id':self.id, 'follow':true};
		
		if self.id in followed_users:
			requete['to_keep'] = True
		
		#user = self.friendships_create(requete)
		followed.append("@".self.screen_name);
		return self
	
	def blacklist(self):
		print("hello world")
		
	# The lower the ratio, the more interesting you are
	def getFollowRatio(self):
		return round(self.data['friends_count'] / (self.data['followers_count']+1), 1)
		
	# The lower the ratio, the more interesting you are
	def getTweetRatio(self):
		return round(self.data['statuses_count'] / self.data['followers_count']+1, 1)
	



def scanURLs(quota):
	print(quota)
	users = self.search(count=quota)
	for user in users:
		user = user(data=user)
		if isinstance(user.url, str):
			a = user.getAlexaRank()
			if isinstance(a, bool):
				print("["+user.screen_name+"] site : "+user.url+" (non classé chez Alexa)")
			else:
				print("["+user.screen_name+"] site : "+user.url+" (rang Alexa "+str(a)+")")
		else:
			print("["+user.screen_name+"] pas de site")

def searchDB(expression="", count=100, page=1, sort=[['screen_name', 1]]):
	if count < 1:
		count = 1
	request = {}
	if len(expression):
		request['description'] = {'$regex' : re.compile(expression, re.I)}
	for s in sort:
		if s[1] > 0:
			s = pymongo.ASCENDING
		else:
			sort[s] = pymongo.DESCENDING
	users = DB.users.find(request, skip=((page-1)*count), limit=count, sort=sort)
	return users

def searchTwitter(expression="", count=100, page=1, sort=[['screen_name', 1]]):
	if count < 1:
		count = 1
	request = {}
	if len(expression):
		request['description'] = {'$regex' : re.compile(expression, re.I)}
	for s in sort:
		if s[1] > 0:
			s = pymongo.ASCENDING
		else:
			sort[s] = pymongo.DESCENDING
	users = DB.users.find(request, skip=((page-1)*count), limit=count, sort=sort)
	return users

def checkIfPossible(request):
	return True

def followPeople(people):
	for person_id in people:
		person = user(person_id)
		if person.shouldFollow():
			person.follow()
		else:
			person.blacklist()
		
		
def unfollowPeople(people):
	for person_id in people:
		person = user(person_id)
		if person.shouldUnfollow():
			person.unfollow()
		else:
			person.whitelist()

def get_user(user_id=None, screen_name=None):
	if user_id != None:
		u = TwitterAPI.get_user(user_id=user_id)
	elif screen_name != None:
		u = TwitterAPI.get_user(screen_name=screen_name)
	else:
		u =  TwitterAPI.me()
	u = u.__dict__['_json']
	return u

def get_absent_user_entries(ids=[]):
	entries = list(DB.users.find({'id':{'$in':ids}}))
	if len(ids) == len(entries):
		return []
	return list(set(ids) - set([x.id for x in entries]))

def get_relations_list(user_id=None, screen_name=None, who='followers'):
	request = ('followers|ids', 'friends|ids')[who=='influencers']
	_ids = []
	_cursor = -1
	if me.can_query(request=request):
		if user_id != None:
			c = tweepy.Cursor((TwitterAPI.followers_ids, TwitterAPI.friends_ids)[who=='influencers'], user_id=user_id, cursor=_cursor)
		elif screen_name != None:
			c = tweepy.Cursor((TwitterAPI.followers_ids, TwitterAPI.friends_ids)[who=='influencers'], screen_name=screen_name, cursor=_cursor)
		me.update_query_limit(request=request)
						
		try:
			for id in c.items():
				_ids.append(id)
				if c.iterator.next_cursor != _cursor:
					me.update_query_limit(request=request)
					_cursor = c.iterator.next_cursor
		finally:
			return _ids

def get_relations(user_id=None, screen_name=None, who='followers', max=2600):
	_users = []
	_ids = []
	_calls = 0
	_cursor = -1
	_per_page_ = 200
	
	todays_metrics = DB.metrics.find_one({'id': user_id, 'day':str(date.today())})
	if todays_metrics != None:
		if who in todays_metrics.keys():
			if 'cursor' in todays_metrics[who].keys():
				_cursor = todays_metrics[who]['cursor']
		else:
			todays_metrics[who] = {'list':[]}
	else:
		todays_metrics = {who:{'list':[]}}
	
	request = ('followers|ids', 'friends|ids')[who=='influencers']
	if me.can_query(request=request):
		if user_id != None:
			c = tweepy.Cursor((TwitterAPI.followers_ids, TwitterAPI.friends_ids)[who=='influencers'], user_id=user_id, cursor=_cursor)
		elif screen_name != None:
			c = tweepy.Cursor((TwitterAPI.followers_ids, TwitterAPI.friends_ids)[who=='influencers'], screen_name=screen_name, cursor=_cursor)
		me.update_query_limit(request=request)
						
		try:
			for id in c.items():
				_ids.append(str(id))
				if c.iterator.next_cursor != _cursor:
					me.update_query_limit(request=request)
					_cursor = c.iterator.next_cursor
			
			if me.can_query(request='users|lookup'):
				for slice in range(0, len(_ids), 100):
					_c_ = TwitterAPI.lookup_users(user_ids=_ids[slice:slice+99], include_entities=True)
					me.update_query_limit(request='users|lookup')
					for user in _c_:
						user = user.__dict__['_json']
						_users.append(user)
						_calls = len(_users) / _per_page_
						
						if len(_users) >= max or (not me.can_query(request=request) and len(_users) % _per_page_ == _per_page_ - 1):
							break
			
		finally:
			if _cursor != None and _cursor not in [0, -1]:
				DB.metrics.update({'id': user_id, 'day':str(date.today())}, {'$set':{who+'.cursor':_cursor}}, upsert=True)
				#_last_cursor_[who][user_id] = _cursor
			else:
				DB.metrics.update({'id': user_id, 'day':str(date.today())}, {'$unset':{who+'.cursor':True}}, upsert=True)
				#if user_id in _last_cursor_[who].keys():
				#	del _last_cursor_[who][user_id]
	
	_ids = list(set(todays_metrics[who]['list']) - set(_ids))
	for already in DB.users.find({'id':{'$in':_ids}}):
		already['lang'] = already['lang'][0:2]
		_users.update({'id':already['id']}, {'$set':already, '$currentDate': {'last_update': True}})
	
	return _users

def get_followers(user_id=None, screen_name=None, max=2600):
	return get_relations(user_id, screen_name, who='followers', max=max)
	
	
def get_influencers(user_id=None, screen_name=None, max=2600):
	return get_relations(user_id, screen_name, who='influencers', max=max)
	
	
def do_auth(id=None, data=None):
	global TwitterAPI, me
	if id == None:
		auth.set_access_token(session.SESSION['access_token'], session.SESSION['access_token_secret'])
	else:
		#if data != None:
		#	me = user(id=id, data=data)
		#else:
		me = user(id=id)
		
		session.SESSION['current_user'] = me.id
		account = DB.accounts.find_one({'id':me.id})
		auth.set_access_token(account['access_token'], account['access_token_secret'])
		session.SESSION['access_token'] = account['access_token']
		session.SESSION['access_token_secret'] = account['access_token_secret']
		
	TwitterAPI = tweepy.API(auth, retry_count=3, compression=True)
	if 'current_user' not in session.SESSION.data.keys():
		login = True
		found = DB.accounts.find_one({'access_token':session.SESSION['access_token']})
		if found:
			session.SESSION['current_user'] = found['id']
			me = user(id=session.SESSION['current_user'])
		else:
			signup = True
			_data = get_user()
			session.SESSION['current_user'] = _data['id']
			me = user(id=session.SESSION['current_user'], data=_data)
			DB.accounts.insert_one({
				'id'					:	me.id,
				'name'					:	me.name,
				'creation'				:	datetime.now(),
				'ip'					:	request.ip,
				'offer'					:	'free',
				'access_token'			:	session.SESSION.data['access_token'],
				'access_token_secret'	:	session.SESSION.data['access_token_secret']
			})
	else:
		me = user(id=session.SESSION['current_user'])

def makebrowsable():
	to_normalize = DB.users.find({'sortable_username':{'$exists':False}})
	for a_user in to_normalize:
		DB.users.update({'id':a_user['id']}, {'$currentDate': {'last_update': True}, '$set':{'sortable_username':a_user['name'].lower()}})

def initaccounts():
	anciens = DB.metrics.distinct("id", {'day':str(date.today())})
	print(config.time()+" "+str(len(anciens))+" comptes ont des métriques.")
		
	if len(anciens):
		client = DB.accounts.find_one({'id':{'$nin':anciens}})
	else:
		client = DB.accounts.find_one()
	
	if client == None:
		_client_ = DB.metrics.find_one({
			'day':str(date.today()),
			'$or': [
				{'followers.cursor':{'$exists':True}},
				{'influencers.cursor':{'$exists':True}},
				{'newcomers.cursor':{'$exists':True}},
				{'quitters.cursor':{'$exists':True}}
			]}
		)
		if _client_ != None:
			client = DB.accounts.find_one({'id':_client_['id']})
	
	if client != None:
		#print(client)
		do_auth(client['id'], data=client)
		newbie = user(id=client['id'])
		print(config.time()+" Compte sans métrique trouvé : "+newbie.name)
		newbie.generate_metrics_entry()
		anciens.append(newbie.id)

"""

"""
def updateaccounts():
	clients = DB.accounts.find()
	for client in clients:
		do_auth(client['id'], data=client)
		me.retrieve_api_limits()
		newentry = get_user(client['id'])
		newentry['lang'] = newentry['lang'][0:2]
		DB.users.update_one(
			{'id': client['id']},
			{'$set': newentry, '$currentDate': {'last_update': True}}
		)
	
	#"""
	to_document = DB.users.find({'links.wikipedia':{'$exists':False}}).sort('followers_count',mongo.DESC)[0:50]
	for a_user in to_document:
		u = user(a_user['id'])
		u.lang = u.lang[0:2]
		wiki = u.getWikiURL()
		#print(wiki)
		if len(wiki):
			DB.users.update({'id':a_user['id']}, {'$currentDate': {'last_update': True}, '$set':{'links.wikipedia':wiki}})
		else:
			DB.users.update({'id':a_user['id']}, {'$currentDate': {'last_update': True}, '$set':{'links.wikipedia':[]}})
	
	to_document = DB.users.find({'links.linkedin':{'$exists':False}}).sort('followers_count',mongo.DESC)[0:10]
	for a_user in to_document:
		u = user(a_user['id'])
		linkedin = u.getLinkedInURL()
		
		if len(linkedin):
			DB.users.update({'id':a_user['id']}, {'$currentDate': {'last_update': True}, '$set':{'links.linkedin':linkedin}})
		else:
			DB.users.update({'id':a_user['id']}, {'$currentDate': {'last_update': True}, '$set':{'links.linkedin':[]}})
	
	
def monitor_realtime_behaviors():
	
	clients = DB.accounts.find()
	mapping = {'_newf_':'newcomers', '_leftf_':'quitters', '_newi_':'risingstars', '_lefti_':'nongrata'}
	for client in clients:
		do_auth(client['id'])
		print("\n")
		print('---------------------------')
		print("Compte de "+client['name'])
		me.retrieve_api_limits()
		current = DB.users.find_one({'id':me.id})
		compare = 'details' in current.keys()
		if compare:
			print("Les comportements sont déjà présents")
			comparaison = {
				'followers'		:	me.details['followers'],
				'influencers'	:	me.details['influencers'],
				'newcomers'		:	me.details['newcomers'],
				'quitters'		:	me.details['quitters'],
				'risingstars'	:	me.details['risingstars'],
				'nongrata'		:	me.details['nongrata']
			}
		else:
			print("Les comportements sont à initialiser")
			me.details = {'followers':[], 'influencers':[], 'newcomers':{}, 'quitters':{}, 'risingstars':{}, 'nongrata':{}}
		
		print("Voici les stats de ce compte:")
		me.details['followers'] = get_relations_list(user_id=me.id, who='followers')
		me.details['influencers'] = get_relations_list(user_id=me.id, who='influencers')
		
		print(str(len(me.details['followers']))+' followers ont été trouvés')
		print(str(len(me.details['influencers']))+' influenceurs ont été trouvés')
		
		if compare:
			news = {
				'_newf_'	:	list(set(me.details['followers']) - set(comparaison['followers'])),
				'_leftf_'	:	list(set(comparaison['followers']) - set(me.details['followers'])),
				'_newi_'	:	list(set(me.details['influencers']) - set(comparaison['influencers'])),
				'_lefti_'	:	list(set(comparaison['influencers']) - set(me.details['influencers']))
			}
			for k in news:
				for id in news[k]:
					if str(id) in comparaison[mapping[k]]:
						comparaison[mapping[k]][str(id)].append(time.time())
					else:
						comparaison[mapping[k]][str(id)] = [time.time()]
			me.details = {
				'followers'		:	me.details['followers'],
				'influencers'	:	me.details['influencers'],
				'newcomers'		:	comparaison['newcomers'],
				'quitters'		:	comparaison['quitters'],
				'risingstars'	:	comparaison['risingstars'],
				'nongrata'		:	comparaison['nongrata']
			}
		else:
			me.details = {
				'followers'		:	me.details['followers'],
				'influencers'	:	me.details['influencers'],
				'newcomers'		:	{},
				'quitters'		:	{},
				'risingstars'	:	{},
				'nongrata'		:	{}
			}


"""

def scan_descriptions():
	import slugify, operator
	irrelevant = ['are', 'the', 'from', 'http', 'https', 'with', 'des', 'les', 'and', 'for']
	users = DB.users.find()
	count = {}
	for user in users:
		t = slugify.slugify(user['description']).split('-')
		#print(t)
		for word in t:
			if len(word) == 1:
				continue
			if word not in count.keys():
				count[word] = 0
			count[word] += 1
	
	for word in count:
		if count[word] <= 2 or len(word) <= 2:
			irrelevant.append(word)
	
	for w in irrelevant:
		if w in count.keys():
			del count[w]
	
	#print(count.items())
	_words_ = sorted(count.items(), key=operator.itemgetter(1), reverse=True)
	print(_words_)
	#for _word_ in _words_:
	#	print(_word_, _words_[_word_])
		#print(_words_[_word_]+'		: '+_count_[_word_]+' occurences')

"""

def dispatch():
	if request.called_method == 'network':
		if 'access_token' not in session.SESSION.data.keys():
			output.echo('Location: '+request.exacthost+'/twitter/login', hook='http-headers', overwrite=True)
			output.echo('Status: 302 Found', hook='http-headers')
			output.include('null', 'root')
		else:
			output.include('twitter.browser', 'root', overwrite=True)
			output.echo(me.name, hook='User Name')
			output.echo(me.profile_image_url.replace('_normal',''), hook='Twitter profile picture')
			if 'details' in me.data.keys() and 'influencers' in me.data['details'].keys():
				languages = list(set([x[0:2] for x in DB.users.distinct('lang', {'id':{'$in':me.details['influencers']}})]))
				req = {'id':{'$in':me.details['influencers']}}
				if 'lang' in request.params.keys() and request.params['lang'] in languages:
					req['lang'] = request.params['lang']
				
				users = DB.users.find(req).sort('sortable_username', mongo.ASC)
				_count_ = users.count()
				_pages_ = int(_count_ / 100) + int(bool(_count_ % 100))
				current_page = min(1 if 'page' not in request.params.keys() else int(request.params['page']), _pages_)
				users = users[(current_page-1)*100:(current_page*100)]
				
				for u in users:
					u = user(id=u['id'], data=u)
					entry = {
						'username'				:	u.name,
						'screen_name'			:	u.screen_name,
						'image'					:	u.profile_image_url.replace('_normal',''),
						'description'			:	u.description,
						'language'				:	u.lang,
						'nb_tweets'				:	output.shorten(u.statuses_count),
						'nb_influencers'		:	output.shorten(u.friends_count),
						'nb_followers'			:	output.shorten(u.followers_count),
						'relationship-status'	:	' '.join([
														('not-following', 'following')[u.id in me.details['influencers']],
														('not-follower', 'follower')[u.id in me.details['followers']],
														('not-newcomer', 'newcomer')[str(u.id) in me.details['newcomers'].keys() and me.details['newcomers'][str(u.id)].pop() > time.time() - 86400],
														('not-quitter', 'quitter')[str(u.id) in me.details['newcomers'].keys()],
													]),
						'external-links'		:	'',
						'current-relationships'	:	''
					}
					if 'links' in u.data.keys():
						if 'wikipedia' in u.links.keys() and len(u.links['wikipedia']):
							found = False
							for lg in list(set([u.lang, 'en', 'fr'])):
								if lg in u.links['wikipedia'].keys():
									entry['external-links'] += '<a style="color:white;" target="_blank" href="'+u.links['wikipedia'][lg]['url']+'"><i class="fa fa-wikipedia-w"></i></a>'
									found = True
									break
							if not found:
								entry['external-links'] += '<a style="color:white;" target="_blank" href="'+(u.links['wikipedia'].popitem()[1]['url'])+'"><i class="fa fa-wikipedia-w"></i></a>'
					output.include('twitter.block.userentry', hook='user-entries', fill=entry)
				
				#output.echo(, hook='current-relationships')
				output.include('twitter.block.actionbutton', hook='buttons', fill={'id-twittos':u.id})
				
				output.echo(output.paginate(style='numbers', current=current_page, params=request.params, criterion='page', last=_pages_), hook='number-pagination')
				output.echo(output.paginate(style='languages', current=('' if 'lang' not in request.params.keys() else request.params['lang']) , params={}, criterion='lang', options=list(languages)), hook='language-pagination')
				
		
	elif request.called_method == 'dashboard':
		if 'access_token' not in session.SESSION.data.keys():
			output.echo('Location: '+request.exacthost+'/twitter/login', hook='http-headers', overwrite=True)
			output.echo('Status: 302 Found', hook='http-headers')
			output.include('null', 'root')
		else:
			count_metrics = DB.metrics.count({'id':me.id})
			if count_metrics > 0:
				output.include('twitter.dashboard', 'root', overwrite=True)
				output.echo(me.name, hook='User Name')
				output.echo(me.profile_image_url.replace('_normal',''), hook='Twitter profile picture')
				today = DB.metrics.find({'id':me.id}).sort('day', mongo.DESC)[0]
				today_map = OrderedDict()
				
				if request.called_submethod == '':
					if 'influencers' in today.keys():	
						today_map['influencers'] = {
							'bigcounter-icon'			:	'user',
							'bigcounter-name'			:	'Your influencers',
							'bigcounter-title'			:	'Influencers',
							'bigcounter-color'			:	'',
							'bigcounter-length-medium'	:	4,
							'bigcounter-length-short'	:	12,
							'bigcounter-abs'			:	today['influencers']['number']
						}
					if 'followers' in today.keys():
						today_map['followers'] = {
							'bigcounter-icon'			:	'user',
							'bigcounter-name'			:	'Your followers',
							'bigcounter-title'			:	'Followers',
							'bigcounter-color'			:	'',
							'bigcounter-length-medium'	:	4,
							'bigcounter-length-short'	:	12,
							'bigcounter-abs'			:	today['followers']['number']
						}
					if len(today_map) == 2:
						today_map['ratio_influence'] = {
							'bigcounter-icon'			:	'user',
							'bigcounter-name'			:	'Your influence ratio',
							'bigcounter-title'			:	'Ratio',
							'bigcounter-color'			:	'green',
							'bigcounter-length-medium'	:	4,
							'bigcounter-length-short'	:	12,
							'bigcounter-abs'			:	round(today['followers']['number'] / today['influencers']['number'], 3)
						}
						today['ratio_influence'] = {'number':round(today['followers']['number'] / today['influencers']['number'], 3)}
					
					if count_metrics > 7:
						previous = DB.metrics.find({'id':me.id}).sort('day', mongo.DESC)[7]
						previous_map = OrderedDict()
						if 'followers' in previous.keys() and 'influencers' in previous.keys():
							previous['ratio_influence'] = {'number':round(previous['followers']['number'] / previous['influencers']['number'], 3)}
						
						for i in today_map.keys():
							if i in previous.keys():
								previous_map[i] = {
									'bigcounter-rate-color'		:	('green','red')[previous[i]['number'] > today[i]['number']],
									'bigcounter-rate-sign'		:	('asc','desc')[previous[i]['number'] > today[i]['number']],
									'bigcounter-rate'			:	round(fabs(today[i]['number'] - previous[i]['number']) / previous[i]['number'], 2),
									'bigcounter-variation-text'	:	('lower','higher')[previous[i]['number'] < today[i]['number']]+' than last week'
								}
						
						for i in today_map:
							if i in previous_map:
								today_map[i].update(previous_map[i])
								output.include('twitter.block.headercounter', hook='headercounter', fill=today_map[i])
							else:
								output.include('twitter.block.headercounter-wo-rate', hook='headercounter', fill=today_map[i])
					else:
						for i in today_map:
							output.include('twitter.block.headercounter-wo-rate', hook='headercounter', fill=today_map[i])
					
					output.echo('', hook='donut-chart-languages')
					
				elif request.called_submethod == 'variations':
					today_map['newcomers'] = {
						'bigcounter-icon'			:	'user',
						'bigcounter-name'			:	'Newcomers',
						'bigcounter-title'			:	'Newcomers',
						'bigcounter-length-medium'	:	4,
						'bigcounter-length-short'	:	12,
						'bigcounter-color'			:	'',
						'bigcounter-abs'			:	0 if 'newcomers' not in today.keys() else today['newcomers']['number']
					}
					
					today_map['quitters'] = {
						'bigcounter-icon'			:	'user',
						'bigcounter-name'			:	'Quitters',
						'bigcounter-title'			:	'Quitters',
						'bigcounter-color'			:	'',
						'bigcounter-length-medium'	:	4,
						'bigcounter-length-short'	:	12,
						'bigcounter-abs'			:	0 if 'quitters' not in today.keys() else 0-today['quitters']['number']
					}
						
					today_map['net_variation'] = {
						'bigcounter-icon'			:	'user',
						'bigcounter-name'			:	'Your net variation',
						'bigcounter-title'			:	'Net variation',
						'bigcounter-color'			:	'green',
						'bigcounter-length-medium'	:	4,
						'bigcounter-length-short'	:	12,
						'bigcounter-abs'			:	today_map['newcomers']['bigcounter-abs'] + today_map['quitters']['bigcounter-abs']
					}
					
					if count_metrics > 7:
						previous = DB.metrics.find({'id':me.id}).sort('day', mongo.DESC)[7]
						previous_map = OrderedDict()
						#if 'followers' in previous.keys() and 'influencers' in previous.keys():
						#	previous['ratio_influence'] = {'number':round(previous['followers']['number'] / previous['influencers']['number'], 2)}
						for i in today_map.keys():
							if i in previous.keys():
								previous_map[i] = {
									'bigcounter-rate-color'		:	('green','red')[previous[i]['number'] > today[i]['number']],
									'bigcounter-rate-sign'		:	('asc','desc')[previous[i]['number'] > today[i]['number']],
									'bigcounter-rate'			:	fabs(today[i]['number'] - previous[i]['number']) / previous[i]['number'],
									'bigcounter-variation-text'	:	('lower','higher')[previous[i]['number'] < today[i]['number']]+' than last week'
								}
						
						for i in today_map:
							if i in previous_map:
								today_map[i].update(previous_map[i])
								output.include('twitter.block.headercounter', hook='headercounter', fill=today_map[i])
							else:
								output.include('twitter.block.headercounter-wo-rate', hook='headercounter', fill=today_map[i])
					else:
						for i in today_map:
							output.include('twitter.block.headercounter-wo-rate', hook='headercounter', fill=today_map[i])
					
					output.echo('', hook='donut-chart-languages')
					
				elif request.called_submethod in ['influencers', 'followers']:
					target = request.called_submethod
					
					if target in today.keys():	
						today_map['avg_influencers'] = {
							'bigcounter-icon'			:	'user',
							'bigcounter-name'			:	'Their influencers (avg)',
							'bigcounter-title'			:	'Influencers',
							'bigcounter-color'			:	'',
							'bigcounter-length-medium'	:	4,
							'bigcounter-length-short'	:	12,
							'bigcounter-abs'			:	output.shorten(today[target]['avg_influencers'])
						}
						today_map['avg_followers'] = {
							'bigcounter-icon'			:	'user',
							'bigcounter-name'			:	'Their followers (avg)',
							'bigcounter-title'			:	'Followers',
							'bigcounter-color'			:	'',
							'bigcounter-length-medium'	:	4,
							'bigcounter-length-short'	:	12,
							'bigcounter-abs'			:	output.shorten(today[target]['avg_followers'])
						}
						today_map['ratio_influence'] = {
							'bigcounter-icon'			:	'user',
							'bigcounter-name'			:	'Influence ratio (avg)',
							'bigcounter-title'			:	'Ratio',
							'bigcounter-color'			:	'green',
							'bigcounter-length-medium'	:	4,
							'bigcounter-length-short'	:	12,
							'bigcounter-abs'			:	output.shorten(today[target]['ratio_influence'])
						}
					else:
						output.echo('', hook='headercounter')

					if count_metrics > 7:
						previous = DB.metrics.find({'id':me.id}).sort('day', mongo.DESC)[7]
						previous_map = OrderedDict()
						if target in previous.keys():
							previous['ratio_influence'] = {'number':round(previous['followers']['number'] / previous['influencers']['number'], 3)}
						
						for i in today_map.keys():
							if i in previous[target].keys():
								previous_map[i] = {
									'bigcounter-rate-color'		:	('green','red')[previous[target][i] > today[target][i]],
									'bigcounter-rate-sign'		:	('asc','desc')[previous[target][i] > today[target][i]],
									'bigcounter-rate'			:	round(fabs(today[target][i] - previous[target][i]) / previous[target][i], 3),
									'bigcounter-variation-text'	:	('lower','higher')[previous[target][i] < today[target][i]]+' than last week'
								}
						
						for i in today_map:
							if i in previous_map:
								today_map[i].update(previous_map[i])
								output.include('twitter.block.headercounter', hook='headercounter', fill=today_map[i])
							else:
								output.include('twitter.block.headercounter-wo-rate', hook='headercounter', fill=today_map[i])
					else:
						for i in today_map:
							output.include('twitter.block.headercounter-wo-rate', hook='headercounter', fill=today_map[i])
					
					
					if target in today.keys():
						language_map = {}
						
						language_map['item-label-list'] = []
						language_map['item-value-list'] = []
						language_map['item-color-list'] = []
						language_map['table-items'] = []
						total = sum(today[target]['languages'].values())
						_colors_ = output.get_colorcodes(len(today[target]['languages']), rgb=False)
						_sum_ = 100
						_summed_ = total
						languages = sorted(today[target]['languages'].items(), key=lambda x: x[1], reverse=True)
						
						strings = []
						
						for language, people in languages:
							
							if _sum_ <= 0:
								language_map['item-label-list'].append('Others')
								language_map['item-value-list'].append(output.shorten(_sum_))
								language_map['item-color-list'].append('#CCCCCC')
								language_map['table-items'].append("<tr><td>Others</td><td>&nbsp;<b>"+output.shorten(_summed_)+"</b></td></tr>")
								strings.append('{ name: "Others", y: '+output.shorten(_summed_)+' }')
								break
							
							else:
								fraction = int(round(people / total * 100, 1))
								_sum_ -= fraction
								_summed_ -= people
								img = "<img style='margin-right:3px;display:inline-block;' src='/static/img/flags/lang/"+language+".png'>"
								
								language_map['item-label-list'].append(language.upper())
								language_map['item-value-list'].append(output.shorten(fraction))
								language_map['item-color-list'].append(_colors_[len(language_map['item-color-list'])])
								language_map['table-items'].append("<tr><td>"+img+language.upper()+"</td><td>&nbsp;<b>"+str(people)+"</b></td></tr>")
								strings.append('{ name: "'+img+language.upper()+'", y: '+str(people)+' }')
							
						language_map['item-label-list'] = '["'+'","'.join(language_map['item-label-list'])+'"]'
						language_map['item-color-list'] = '["'+'","'.join(language_map['item-color-list'])+'"]'
						language_map['table-items'] = ''.join(language_map['table-items'])
						language_map['item-value-list'] = '['+','.join(language_map['item-value-list'])+']'
						output.include('twitter.block.donut-chart', hook='donut-chart-languages', fill={'donut-title':"Languages",'donut-data':','.join(strings)})
					else:
						output.echo('', hook='donut-chart-languages')
				
				else:
					raise PageNotFoundException()
				
				
				date_map = {'chart-data':[]}
				if 'start' not in request.params or 'end' not in request.params:
					_now_ = time.time()
					_end_ = datetime.fromtimestamp(_now_)
					_start_ = datetime.fromtimestamp(_now_ - 7 * 86400)
					
				else:
					startmonth, startday, startyear = '/'.split(request.params['start'])
					endmonth, endday, endyear = '/'.split(request.params['end'])
					_start_ = datetime(int(startyear), int(startmonth), int(startday), 0, 0, 0)
					_end_ = datetime(int(endyear), int(endmonth), int(endday), 23, 59, 59)
					
				days = DB.metrics.find({'id':me.id, 'time':{'$gt':_start_, '$lt':_end_}}).sort('day', mongo.ASC)
				months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
				_charts_ = OrderedDict()
				
				for key in today_map.keys():
					if request.called_submethod == 'variations' and key != 'net_variation':
						_charts_['movements'] = []
						_charts_[key] = []
					else:
						_charts_[key] = []
				
				tabheaders = ''
				tabcontents = ''
				tabdata = ''
				chartkeys = []
				chartnames = []
				
				for day in days:
					chartkeys.append(day['day'])
					_, the_month, the_day = day['day'].split('-')
					the_right_day = months[int(the_month)-1]+' '+the_day
					chartnames.append(the_right_day)
					for key in _charts_:
						if request.called_submethod == '':
							if key != 'ratio_influence':
								_charts_[key].append("{name:'"+the_right_day+"',y:"+str(day[key]['number'])+"}")
							else:
								_charts_[key].append("{name:'"+the_right_day+"',y:"+str(round(day['followers']['number'] / day['influencers']['number'], 3))+"}")
							
						elif request.called_submethod == 'variations':
							if key != 'net_variation':
								if key == 'newcomers':
									to_add = 0 if key not in day.keys() else day[key]['number']
								else:
									to_add = 0 if key not in day.keys() else 0 - day[key]['number']
								
								_charts_[key].append("{name:'"+the_right_day+"',y:"+str(to_add)+"}")
								#_charts_['movements'].append("{name:'"+the_right_day+"',y:"+str(to_add)+"}")
							else:
								_newcomers_ = 0 if 'newcomers' not in day.keys() else day['newcomers']['number']
								_quitters_ = 0 if 'quitters' not in day.keys() else day['quitters']['number']
								_charts_[key].append("{name:'"+the_right_day+"',y:"+str(_newcomers_ - _quitters_)+"}")
						else:
							_charts_[key].append("{name:'"+the_right_day+"',y:"+str(round(day[request.called_submethod][key], 2))+"}")
				
				chartkeys = '["'+'","'.join(chartnames)+'"]'
				
				string = string2 = ""
				for k, v in _charts_.items():
					if request.called_submethod == 'variations':
						if k == 'movements':
							_cc_ = {'quitters':'rgb(200,100,100)', 'newcomers':'rgb(100,200,100)'}
							for i in ['quitters', 'newcomers']:
								string += ",{type:'areaspline',marker:{enabled:false}, color:'"+_cc_[i]
								string += "', name:'"+today_map[i]['bigcounter-name']+"', data:["
								string += ','.join(_charts_[i])+"]}"
								string2 += (",{type:'areaspline',marker:{enabled:false}, color:'"+_cc_[i]+"', name:'"+today_map[i]['bigcounter-name']+"', data:["+','.join(_charts_[i])+"]}").replace("'", '"')
							
							# Données cumulées + et -
							date_map['chart-data'].append(string[1:])
							tabdata = ('', ',')[int(bool(len(tabdata)))]+"\n{container:'plus-and-minus', title:'Variations', data:["+string2[1:]+"]}"
							tabcontents += '<div role="tabpanel" class="tab-pane '+('active','')[int(bool(len(tabcontents)))]+'" id="chart_tab_plus-and-minus" style="height:270px;"></div>'
							tabheaders += '<li role="presentation" class="'+('active','')[int(bool(len(tabheaders)))]+'"><a href="#chart_tab_plus-and-minus" aria-controls="profile" role="tab" data-toggle="tab">Variations</a></li>'
						
						elif k in ['quitters', 'newcomers']:
							pass
							
						else:
							string = "{type:'spline',marker:{enabled:false}, color:'rgb(220,180,110)', name:'"+today_map[k]['bigcounter-name']+"', data:["+','.join(v)+"]}"
							string2 = ("{type:'spline',marker:{enabled:false}, color:'rgb(220,180,110)', name:'"+today_map[k]['bigcounter-name']+"', data:["+','.join(v)+"]}").replace("'", '"')
							tabdata += ('', ',')[int(bool(len(tabdata)))]+"\n{container:'"+k+"', title:'"+today_map[k]['bigcounter-name']+"', data:["+string2+"]}"
						
							tabcontents += '<div role="tabpanel" class="tab-pane '+('active','')[int(bool(len(tabcontents)))]+'" id="chart_tab_'+k+'" style="height:270px;"></div>'
							tabheaders += '<li role="presentation" class="'+('active','')[int(bool(len(tabheaders)))]+'"><a href="#chart_tab_'+k+'" aria-controls="profile" role="tab" data-toggle="tab">'+today_map[k]['bigcounter-title']+'</a></li>'
						
						for i in ['quitters', 'newcomers']:
							if i in _charts_.keys():
								del _charts_[i]
								
					else:
						string = "{type:'spline',marker:{enabled:false}, name:'"+today_map[k]['bigcounter-name']+"', data:["+','.join(v)+"]}"
						string2 = ("{type:'spline',marker:{enabled:false}, name:'"+today_map[k]['bigcounter-name']+"', data:["+','.join(v)+"]}").replace("'", '"')
						date_map['chart-data'].append(string)
						tabheaders += '<li role="presentation" class="'+('active','')[int(bool(len(tabcontents)))]+'"><a href="#chart_tab_'+k+'" aria-controls="profile" role="tab" data-toggle="tab">'+today_map[k]['bigcounter-title']+'</a></li>'
						tabcontents += '<div role="tabpanel" class="tab-pane '+('active','')[int(bool(len(tabcontents)))]+'" id="chart_tab_'+k+'" style="height:270px;"></div>'
						tabdata += ('', ',')[int(bool(len(tabdata)))]+"\n{container:'"+k+"', title:'"+today_map[k]['bigcounter-name']+"', data:["+string2+"]}"
				
				date_map = {'chart-data':','.join(date_map['chart-data']), 'tabs-header':tabheaders, 'tabs-content':tabcontents, 'chart-keys':chartkeys, 'tabdata':'['+tabdata+']'}
				if 'json' in request.params.keys():
					output.echo('Content-Type: text/json', hook='http-headers', overwrite=True)
					output.echo('['+date_map['chart-data']+']', hook='root', overwrite=True)
				else:
					output.include('twitter.block.date-chart', hook='combined-chart-date', fill=date_map)
				
			else:
				output.include('twitter.metrics.wait', 'root', overwrite=True)
		
	elif request.called_method == 'callback':
		if 'denied' in request.params:
			del session.SESSION['request_token']
			del session.SESSION['request_token_secret']
			output.echo('Location: '+request.exacthost+'/twitter/login?reason=authorization_denied', hook='http-headers', overwrite=True)
			output.include('null', 'root')
		elif 'access_token' not in session.SESSION.data.keys():
			access_credentials = get_access_token(consumer_key, consumer_secret)
			session.SESSION['access_token'] = access_credentials[0]
			session.SESSION['access_token_secret'] = access_credentials[1]
			del session.SESSION['request_token']
			del session.SESSION['request_token_secret']
		output.echo('Location: '+request.exacthost+'/twitter/dashboard', hook='http-headers', overwrite=True)
		output.include('null', 'root')
		
	elif request.called_method == 'login':
		if 'login' in request.params.keys():
			request_credentials = authorize(consumer_key, consumer_secret)
			_url = request_credentials[0]
			session.SESSION['request_token'] = request_credentials[1]
			session.SESSION['request_token_secret'] = request_credentials[2]
			output.echo('Location: '+_url, hook='http-headers', overwrite=True)
			output.include('null', 'root', overwrite=True)
		else:
			output.include('twitter.login', 'root', overwrite=True)
		
	elif request.called_method == 'logout':
		request_credentials = authorize(consumer_key, consumer_secret)
		del session.SESSION['access_token']
		del session.SESSION['access_token_secret']
		del session.SESSION['current_user']
		output.echo('Location: '+request.exacthost+'/twitter/login', hook='http-headers', overwrite=True)
		output.include('null', 'root', overwrite=True)
	
	else:
		raise request.PageNotFoundException('not found')



def execute():
	if command.called_method in globals().keys():
		function = globals()[command.called_method]
		if callable(function):
			function()

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
if 'access_token' in session.SESSION.data.keys():
	do_auth()

execute() if __name__ == "__main__" else dispatch()