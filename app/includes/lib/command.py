#!/usr/bin/env python3
# -*- coding: UTF-8 -*-# enable debugging

import config, cgi, os, sys, re, time
from datetime import datetime


"""
[ env ]
{
	'USER': 'root',
	'NODE_PATH': '/usr/lib/nodejs:/usr/lib/node_modules:/usr/share/javascript',
	'SHELL': '/bin/bash',
	'MAIL': '/var/mail/root',
	'SHLVL': '1',
	'LC_CTYPE': 'UTF-8',
	'OLDPWD': '/root',
	'_': '/usr/bin/python3',
	'PWD': '/home/web/projets/python/app/controllers',
	'CONTROLLERS': '/home/web/projets/python/app/controllers',
	'COMP_WORDBREAKS': ' \t\n"\'><;|&(:',
	'XDG_SESSION_ID': 'c18656',
	'LS_OPTIONS': '--color=auto',
	'LOGNAME': 'root',
	'HTTP_COOKIE': '',
	'SESSPATH': '/home/web/projets/python/data/sessiondata',
	'HOME': '/root',
	'TEMPLATES': '/home/web/projets/python/app/views',
	'SSH_CONNECTION': '89.157.145.50 60300 5.135.149.28 22',
	'SSH_CLIENT': '89.157.145.50 60300 22',
	'MODELS': '/home/web/projets/python/app/models',
	'LC_ALL': 'en_US.utf8',
	'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
	'CONFPATH': '/home/web/projets/python/app/includes/config',
	'SSH_TTY': '/dev/pts/0',
	'XDG_RUNTIME_DIR': '/run/user/0',
	'LANGUAGE': 'en_US.UTF-8',
	'APP': '/home/web/projets/python',
	'TERM': 'xterm-256color',
	'LANG': 'en_US.UTF-8'
}
"""

initd = True
params = {}

env = os.environ

request = sys.argv

if len(sys.argv) > 2:
	for i in sys.argv[2:]:
		if ':' in i:
			slices = i.split(':')
			params[slices[0]] = slices[1]
		elif '=' in i:
			slices = i.split('=')
			params[slices[0]] = slices[1]
		elif i[0] == '-':
			for j in i[1:]:
				params[j] = True
		else:
			params[i] = True

method = 'BASH'

called_module = called = sys.argv[0].split("/").pop().split('.')[0]
called_method = sys.argv[1]

_time = datetime.now().timetuple()

starttime = int(round(time.mktime(_time) * 1000))

	
	
	