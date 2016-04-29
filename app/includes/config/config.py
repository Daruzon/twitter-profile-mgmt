#!/usr/bin/env python3
# -*- coding: UTF-8 -*-# enable debugging

import os, sys, json

def set_incpath():
	paths = {'root':os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))}
	paths['libs'] = paths['root']+"/app/includes/lib"
	os.environ['APP'] = paths['root']
	os.environ['SESSPATH'] = paths['sessions'] = paths['root']+"/data/sessiondata"
	os.environ['TEMPLATES'] = paths['templates'] = paths['root']+"/app/views"
	os.environ['CONTROLLERS'] = paths['controllers'] = paths['root']+"/app/controllers"
	os.environ['MODELS'] = paths['models'] = paths['root']+"/app/models"
	
	for p in paths:
		sys.path.append(paths[p])

def headers():
	"""
	HEADERS
	"""
	s = [
		"Content-Type: text/html;charset=utf-8",
		"Details: Not your business"
	]
	return '\n'.join(s)

def json_load(file):
	return json.loads(open(file).read())

def isweb():
	return 'QUERY_STRING' in os.environ.keys()

def time():
	import time
	return time.strftime("[%Y-%m-%d %H:%M:%S]")


set_incpath()

config = json.loads(open(os.environ['APP']+"/app/includes/config/config.json").read())

