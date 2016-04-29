#!/usr/bin/env python3
# coding: utf-8
# enable debugging

if __name__ == "__main__":

	import cgi, cgitb, sys, os, locale, codecs, io, importlib
	from datetime import datetime
	from time import time
		
	#cgitb.enable()
	
	os.environ['CONFPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+"/app/includes/config"
	sys.path.append( os.environ['CONFPATH'] )
	import config
	config.set_incpath()
	
	import request, session, output
	#output.render_headers()
	_error_dev_ = True
	_error_url_ = False
	
	#	Bufferisation
	try:
		__real_stdout__ = sys.stdout
		__buffer_out__ = io.StringIO()
		sys.stdout = __buffer_out__
		
		#output.echo(config.headers(), hook='http-headers')
		controller = importlib.import_module(request.called_module, package=None)
		_error_dev_ = False
		
	except request.PageNotFoundException as e:
		_error_url_ = True
		_error_dev_ = False
	
	except Exception as e:
		import traceback
		exc_type, exc_value, exc_traceback = sys.exc_info()
		
		#print(sys.exc_info())
		
	
	#	Restitution du buffer vers le navigateur
	finally:
		sys.stdout = sys.__stdout__ = codecs.getwriter("utf-8")(sys.__stdout__.detach())
		out = __buffer_out__.getvalue()
		__buffer_out__.close()
		
		# Si erreur 500
		
		if _error_dev_ == True :
			import os
			with open(os.path.dirname(os.path.abspath(__file__))+'/static/errors/500.html', 'r') as content_file:
				content = content_file.read()
			print('Status: 500 Server Error')
			print('Content-Type: text/html')
			print()
			print(content)
			print("<div style='display:none;'>")
			print(repr(traceback.format_tb(exc_traceback)).replace("\\n', '", "',\n '").replace("\\n", "\n"))
			print(exc_value)
			print("</div>")
		
		# Si erreur 404
		elif _error_url_ == True :
			import os
			with open(os.path.dirname(os.path.abspath(__file__))+'/static/errors/404.html', 'r') as content_file:
				content = content_file.read()
			#print('Location: '+os.environ['REQUEST_SCHEME']+'://'+os.environ['HTTP_HOST']+'/static/errors/404.html')
			print('Status: 404 Not Found')
			print('Content-Type: text/html')
			print()
			print(content)
			
		#Sinon
		else:
			output.echo(out)
			
			#	On renvoie les headers de la page
			#	Ces headers peuvent être remplacés via des output.echo vers le hook 'http-headers'
			output.render_headers()
			
			# On renvoie le contenu généré.
			# Tout ce qui a été print a été capturé dans le hook {{main}}.
			output.render_response()
	
else:
	print("Content-Type: text/html;charset=utf-8")
	print()
	print("Bad request")
	
	
