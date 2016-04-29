#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# enable debugging

import sys, os, time, datetime, random
from glob import glob

sys.path.append( os.environ['CONFPATH'] )
import config
config.set_incpath()

import session

templates = {'main':''}
rendered = False
coloured = True
cookies = ''

colors = {
	'red'	:	[255,50, 50],
	'green'	:	[100,180,100],
	'blue'	:	[40, 110, 170],
	'purple':	[140, 30, 200],
	'orange':	[220, 150, 40],
	'brown'	:	[150, 100, 50],
	'pink'	:	[255, 100, 180]
}

def shorten(figure):
	letter = ''
	if figure >= 1000:
		letter = 'k'
		figure = figure / 1000
		if figure >= 1000:
			letter = 'm'
			figure = figure / 1000
	
	if figure > 100:
		figure = int(figure)
	elif figure > 10:
		figure = round(figure, 1)
	else:
		figure = round(figure, 2)
	
	return str(figure)+letter
	
		
def echo(string, hook='main', overwrite=False, fill={}):
	if overwrite or (hook not in templates):
		templates[hook] = ''
	to_insert = str(string)
	
	if len(fill):
		for i in fill:
			_hook_ = "{{"+i+"}}"
			if _hook_ in to_insert:
				to_insert = to_insert.replace(_hook_, str(fill[i]))
	
	templates[hook] += to_insert+"\n"
	

def include(template='null', hook='main', overwrite=False, fill={}):
	found = glob(os.environ['TEMPLATES']+'/'+template+'.html') + glob(os.environ['TEMPLATES']+'/*/'+template+'.html')
	t = open(found[0]).read()
	echo(t, hook=hook, overwrite=overwrite, fill=fill)
	
def get(template='null'):
	found = glob(os.environ['TEMPLATES']+'/'+template+'.html') + glob(os.environ['TEMPLATES']+'/*/'+template+'.html')
	return open(found[0]).read().decode("utf-8", "strict")

def render_headers():
	if 'http-headers' in templates.keys():
		print(templates['http-headers'])
		print("Generated-with: Custom headers")
		
	else:
		templates['http-headers'] = ''
		print("Generated-with: Default headers")
	
	if 'Content-Type' not in templates['http-headers']:# and 'Location:' not in templates['http-headers']:
		print("Content-Type: text/html;charset=utf-8")
	print(str(session.SESSION.output()))
	print()
		

def get_colorcodes(num=6, rgb=True):
	conversion = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F']
	_colors_ = []
	_c_ = list(colors.values())
	for a in range(0, num):
		color = random.choice( range(len(_c_)) )
		color_code = ','.join([str(i) for i in _c_[color]])
		del _c_[color]
		if not len(_c_):
			_c_.append([30, 30, 30])
		
		if not rgb:
			_code_ = color_code.split(',')
			for i in [0,1,2]:
				_code_[i] = conversion[int(int(_code_[i])/16)] + conversion[int(_code_[i])%16]
			
			_colors_.append("#"+''.join(_code_))
		
		else:
			_colors_.append("rgb("+color_code+")")
	
	return _colors_
	


def render_response():
	done = []
	
	for t in templates.keys():
		for _t_ in templates.keys():
			if t == _t_ or _t_ in done:
				continue
			
			needle = templates[t]
			hook = "{{"+t+"}}"
			haystack = templates[_t_]
			if hook in haystack:
				templates[_t_] = haystack.replace("{{"+t+"}}", needle)
				done.append(t)
				break
	
	for t in done:
		del templates[t]
	
	rendered = True
	
	
	print(templates['root'])
	
include('html.default', 'root')
	
