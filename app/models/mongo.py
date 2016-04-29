#!/usr/bin/env python3
# coding: utf-8
# enable debugging

import pymongo, json, sys, os

sys.path.append( os.environ['CONFPATH'] )
import config
config.set_incpath()

ASC = pymongo.ASCENDING
DESC = pymongo.DESCENDING

class db:
	def __init__(self, dbname):
		_conf = config.config
		db = _conf['databases'][dbname]
		client = pymongo.MongoClient("mongodb://"+db['user']+":"+db['pass']+"@"+db['host'])
		self.__db = client[dbname]
		for col in self.__db.collection_names():
			if col != 'system.indexes':
				setattr(self,col,self.__db[col])
	
	def __getattr__(self, name):
		self.__db[name].insert_one({'test':True})
		self.__db[name].delete_many({})
		setattr(self, name, self.__db[name])
		return self.__db[name]

