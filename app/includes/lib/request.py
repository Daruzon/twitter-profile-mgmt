#!/usr/bin/env python3
# -*- coding: UTF-8 -*-# enable debugging

import config, cgi, os, re, time
from datetime import datetime

class PageNotFoundException(Exception): pass

"""
[ env ]
CONTEXT_DOCUMENT_ROOT, CONTEXT_PREFIX, DOCUMENT_ROOT, GATEWAY_INTERFACE, HTTP_ACCEPT, HTTP_ACCEPT_ENCODING, HTTP_ACCEPT_LANGUAGE,
HTTP_CACHE_CONTROL, HTTP_CONNECTION, HTTP_HOST, HTTP_UPGRADE_INSECURE_REQUESTS, HTTP_USER_AGENT, PATH, QUERY_STRING,
REDIRECT_QUERY_STRING, REDIRECT_STATUS, REDIRECT_URL, REMOTE_ADDR, REMOTE_PORT, REQUEST_METHOD, REQUEST_SCHEME, REQUEST_URI,
SCRIPT_FILENAME, SCRIPT_NAME, SERVER_ADDR, SERVER_ADMIN, SERVER_NAME, SERVER_PORT, SERVER_PROTOCOL, SERVER_SIGNATURE, SERVER_SOFTWARE
"""

initd = True
params = {}

form = dict(cgi.FieldStorage())
for d in form:
	if "[]" in d:
		c = d[:-2]
		params[c] = []
		for e in form[d]:
			
			params[c].append(e.value)
	else:
		params[d] = form[d].value

env = os.environ
#r = array_map_recursive("addslashes", $GLOBALS["_REQUEST"]);

if 'req' not in params.keys():
	params["req"] = ""

request = params["req"].strip()
del params["req"]

# On découpe cette mini-page, on y localise où est écrit le numéro (qui contient des chiffres de 0 à 9 et des virgules), et on l'extrait
pattern = '/([^/:]*):([^/:]*)/'
details = re.findall(pattern, '/'+(request.replace('/', '//'))+'/', re.I | re.S)

for couple in details:
	params[couple[0]] = couple[1]

method = env["REQUEST_METHOD"].lower()
host = env["HTTP_HOST"]
exacturi = env["REQUEST_URI"]
called = '/'.join([a for a in request.split('/') if (len(a) and ':' not in a)])
_breakdown = [i for i in called.split('/') if len(i)]
called_submethod = ''
if len(_breakdown) > 0:
	called_module = _breakdown[0]
	if len(_breakdown) > 1:
		called_method = _breakdown[1]
		if len(_breakdown) > 2:
			called_submethod = _breakdown[2]
	else:
		called_method = 'index'
else:
	called_module = 'home'
	called_method = 'index'

https = 'HTTPS' in env.__dict__.keys()
if https:
	protocol = 'https'
else:
	protocol = 'http'


if called == "":
	called = "root"

exacthost = env['REQUEST_SCHEME']+'://'+env['HTTP_HOST']
exacturl = exacthost+exacturi

if 'HTTP_REFERER' in env:
	referer = env['HTTP_REFERER']
else:
	referer = ''

if 'HTTP_USER_AGENT' in env:
	useragent = env['HTTP_USER_AGENT']

_time = datetime.now().timetuple()

starttime = int(round(time.mktime(_time) * 1000))
ip = env["REMOTE_ADDR"]

if called == 'root' and env['HTTP_HOST'] not in referer and ('from' in params or '.xyz' in referer):
	print('HTTP/1.1 302 Found')
	print('Location: http://www.google.com/')
	exit()

	
	
	