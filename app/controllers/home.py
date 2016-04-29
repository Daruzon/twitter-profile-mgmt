#!/usr/bin/env python3
# coding: utf-8
# enable debugging

import os, sys

sys.path.append( os.environ['CONFPATH'] )
import config
config.set_incpath()

import request, output, session


def dispatch():
	if request.called_method == 'index':
		redirection = ('login', 'dashboard')['access_token' in session.SESSION.data.keys()]
		output.echo("\n".join(['Status: 302 Found', 'Location: '+request.exacthost+'/twitter/'+redirection]), hook='http-headers', overwrite=True)
		output.include('null', 'root', overwrite=True)
		#output.echo(redirection)
	#else:
	#	print("Content-Type: text/html;charset=utf-8")
	#	print()
	#	print("Hello world")
	#	print(request.exacturl)


dispatch()
	
