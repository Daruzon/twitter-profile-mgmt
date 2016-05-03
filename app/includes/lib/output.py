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
	
def paginate(style='numbers', base='', current=1, params={}, criterion='page', last=1, options=[]):
	if style not in ['numbers', 'languages']:
		style = 'numbers'
	
	if style == 'letters':
		chain = 'abcdefghijklmnopqrstuvwxyz'
		"""
		_ps_ = ''
		_ps_ += '<div style="text-align:center;clear:both;">'
		if len(params):
			_ps_ +='<ul class="pagination pagination-sm lettres"><li><a href="?">Reset</a></li></ul>'
		
		_ps_ += '<ul class="pagination pagination-sm lettres">'
		if 'begins' in params.keys() and params['begins'].find(str(current)
			{if @strpos($chaine, Request.get('params')['begins']) > 0}
			<li>
				<a
					data-toggle="tooltip" data-placement="top" title="{:t('Clavier')} : <span class='glyphicon glyphicon-arrow-left'></span>"
					id="go-left" href="?{:@http_build_query(array_merge($p, array('begins'=>$chaine[strpos($chaine, Request.get('params')['begins'])-1])))}">
			{elseif @Request.get('params')['begins'] == $chaine[0]}
			<li>
				<a
					data-toggle="tooltip" data-placement="top" title="{:t('Clavier')} : <span class='glyphicon glyphicon-arrow-left'></span>"
					id="go-left" href="?{:@http_build_query($p)}">
			{else}
			<li>
				<a
				data-toggle="tooltip" data-placement="top" title="{:t('Clavier')} : <span class='glyphicon glyphicon-arrow-left'></span>"
					id="go-left" href="?{:@http_build_query(array_merge($p, array('begins'=>$chaine[strlen($chaine)-1])))}">
			{/if}<span class="glyphicon glyphicon-chevron-left"></span></a>
			</li>
			<li {:(empty(Request.get('params')['begins'])) ? 'class="active"' : ''}>
				<a href="?{:@http_build_query($p)}">
					{:t("Tout")}
				</a>
			</li>
			{for $i = 0; $i < strlen($chaine); $i++}
			<li {:( ($chaine[$i] == @Request.get('params')['begins']) ? 'class="active"' : '' )}>
				<a href="?{:@http_build_query(array_merge($p, array('begins'=>$chaine[$i])))}">
					{:strtoupper($chaine[$i])}
				</a>
			</li>
			{/for}
			<li>
			{if @strpos(' '.$chaine, @Request.get('params')['begins']) > 0 And @strpos($chaine, @Request.get('params')['begins']) < strlen($chaine)-1}
			<li>
				<a
					data-toggle="tooltip" data-placement="top" title="{:t('Clavier')} : <span class='glyphicon glyphicon-arrow-right'></span>"
					id="go-right" href="?{:http_build_query(@array_merge($p, array('begins'=>$chaine[@(int)strpos($chaine, Request.get('params')['begins'])+1])))}">
			{elseif @empty(Request.get('params')['begins'])}
				<a
					data-toggle="tooltip" data-placement="top" title="{:t('Clavier')} : <span class='glyphicon glyphicon-arrow-right'></span>"
					id="go-right" href="?{:http_build_query(@array_merge($p, array('begins'=>$chaine[0])))}">
			{else}
			<li>
				<a
					data-toggle="tooltip" data-placement="top" title="{:t('Clavier')} : <span class='glyphicon glyphicon-arrow-right'></span>"
					id="go-right" href="?{:@http_build_query($p)}">
			{/if}<span class="glyphicon glyphicon-chevron-right"></span></a>
			</li>
		</ul>
		_ps_ += '</div>'
		
		"""
	
	elif style == 'languages':
		
		
		_ps_ = '<div style="text-align:center;clear:both;">'
		
		if len(current):
			_ps_ +='<ul class="pagination pagination-sm langues" style="margin:5px;"><li><a href="?">Reset</a></li></ul>'
		
		_ps_ += '<ul class="pagination pagination-sm chiffres" style="margin:5px;">'
		
		for i in sorted(options):
			r = params
			r[criterion] = i
			chain = base + '?' + '&'.join([x+'='+y for x,y in r.items()])
			_ps_ += '<li'+('',' class="active"')[i == current]+'><a href="'+chain+'"><img src="/static/img/flags/lang/'+str(i)+'.png"/></a></li>'
		
		_ps_ += '</ul></div>'
		
		
	elif style == 'numbers':
		
		_ps_ = '<div style="text-align:center;clear:both;"><ul class="pagination pagination-sm chiffres" style="margin:5px;">'
		_last_ellipse_ = 0
		
		r = params
		r[criterion] = str(1)
		chain = base + '?' + '&'.join([x+'='+y for x,y in r.items()])
		_ps_ += ('<li'+('',' class="disabled"')[1 == current]+'><a id="go-left" href="'+chain+'"><span class="glyphicon glyphicon-chevron-left"></span></a></li>')
		
		r[criterion] = str(current-1)
		chain = base + '?' + '&'.join([x+'='+y for x,y in r.items()])
		_ps_ += ('<li'+('',' class="disabled"')[1 == current]+'><a id="go-left" href="'+chain+'"><span class="glyphicon glyphicon-arrow-left"></span></a></li>')
		
		for i in range(1, last+1):
			if i not in list(set([1, last]) | set(range(max(1,current-4), min(last, current+4)))):
				if _last_ellipse_ != i-1:
					_ps_ += '<li style="cursor:not-allowed;"><a>...</a></li>'
				_last_ellipse_ = i
			else:
				r = params
				r[criterion] = str(i)
				chain = base + '?' + '&'.join([x+'='+y for x,y in r.items()])
				_ps_ += '<li'+('',' class="active"')[i == current]+'><a href="'+chain+'">'+str(i)+'</a></li>'
			
			
		r = params
		r[criterion] = str(current+1)
		chain = base + '?' + '&'.join([x+'='+y for x,y in r.items()])
		_ps_ += ('<li'+('',' class="disabled"')[last == current]+'><a id="go-right" href="'+chain+'"><span class="glyphicon glyphicon-arrow-right"></span></a></li>')
		
		r[criterion] = str(last)
		chain = base + '?' + '&'.join([x+'='+y for x,y in r.items()])
		_ps_ += ('<li'+('',' class="disabled"')[last == current]+'><a id="go-right" href="'+chain+'"><span class="glyphicon glyphicon-chevron-right"></span></a></li>')
			
		
		_ps_ += '</ul></div>'
		
	
	return _ps_
		
		
		



include('html.default', 'root')
	
