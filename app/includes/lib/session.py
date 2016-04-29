#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# enable debugging

"""
Python Session Handling

Note: A user must have cookies enabled!

TODO:
* Support Named Sessions

Copyright 2010 - Sunjay Varma

Latest Version: http://www.sunjay.ca/download/session.py
"""

import cgi, sys, os, time, errno, hashlib, datetime, http.cookiejar, http.cookies, config, traceback
#from pickle import dump, load, HIGHEST_PROTOCOL, dumps, loads
from json import dump, load

sys.path.append( os.environ['CONFPATH'] )
import config
config.set_incpath()

if "HTTP_COOKIE" not in os.environ:
	os.environ['HTTP_COOKIE'] = ""

SESSION = None
#print("Paramètre")

S_DIR = os.environ['SESSPATH']
S_EXT = ".sess"
S_ID = "__sid__"

TODAY = str(datetime.date.today())
DEBUG = [] # debug messages

if not os.path.exists(S_DIR):
	os.makedirs(S_DIR)

class NoCookiesError(Exception): pass
class NotStarted(Exception): pass

class Session(object):

	def __init__(self):
		self.data = {}
		self.started = False
		self._flock = None
		self.expires = 86400 # delete right away
		
		self.__sid = sid = self.__getsid()
		self.path = os.path.join(S_DIR, sid+S_EXT)

	def isset(self, name):
		"""Is the variable set in the session?"""
		if not self.started:
			raise NotStarted("Session must be started")

		return name in self

	def unset(self, name):
		"""Unset the name from the session"""
		if not self.started:
			raise NotStarted("Session must be started")
		del self[name]

	@staticmethod
	def __newsid():
		"""Create a new session ID"""
		h = hashlib.new("ripemd160")
		line = str(time.time()/time.clock()**-1)+str(os.getpid())
		h.update(line.encode('utf-8'))
		return h.hexdigest()

	def __getsid(self):
		"""Get the current session ID or return a new one"""
		# first, try to load the sid from the GET or POST forms
		form = cgi.FieldStorage()
		if S_ID in form.__dict__.keys():
			sid = form[S_ID].value
			return sid

		# then try to load the sid from the HTTP cookie
		self.cookie = http.cookies.SimpleCookie()
		if 'HTTP_COOKIE' in os.environ.keys():
			self.cookie.load(os.environ['HTTP_COOKIE'])

			if S_ID in self.cookie:
				sid = self.cookie[S_ID].value
				return sid
		elif not config.isweb():
			raise NoCookiesError("Could not find any cookies")

		# if all else fails, return a new sid
		return self.__newsid()

	def getsid(self):
		"""
		Return the name and value that the sid needs to have in a GET or POST
		request
		"""
		if not self.started:
			raise NotStarted("Session must be started")
		return (S_ID, self.__sid)

	def start(self):
		"""Start the session"""
		if self.started:
			return True # session cannot be started more than once per script
		elif not config.isweb():
			self.started = True
			return True
		
		self._flock = FileLock(self.path)
		self._flock.acquire()
		
		# load the session if it exists
		if os.path.exists(self.path):
			with open(self.path, "r") as f:
				self.data = dict(load(f))
				self.data["__date_loaded__"] = TODAY

		else: # create a session
			with open(self.path, "w") as f:
				self.data = {"__date_loaded__":TODAY}

		# the session is officially started!
		self.started = True
		
		# store the sid in the cookie
		self.cookie[S_ID] = self.__sid
		self.cookie[S_ID]["expires"] = str(self.expires)
		self.cookie[S_ID]["version"] = "1"

		return True

	def commit(self):
		if config.isweb():
			"""Commit the changes to the session"""
			if not self.started:
				raise NotStarted("Session must be started")
			with open(self.path, "w") as f:
				dump(self.data, f, sort_keys = True, indent = 4, ensure_ascii=False)

	def destroy(self):
		"""Destroy the session"""
		if not self.started:
			raise NotStarted("Session must be started")
		self.commit()
		os.delete(self.path)
		if self._flock:
			self._flock.release()
		self.started = False

	def output(self):
		"""Commit changes and send headers."""
		if not self.started:
			raise NotStarted("Session must be started")
		self.commit()
		return self.cookie.output()

	def setdefault(self, item, default=None):
		if not self.started:
			raise NotStarted("Session must be started")
		if not self.isset(item):
			self[item] = default

		return self[item]
		
	def set_expires(self, days):
		"""Sets the expiration of the cookie"""
		date = datetime.date.today() + datetime.timedelta(days=days)
		self.expires = date.strftime("%a, %d-%b-%Y %H:%M:%S PST")
		self.cookie[S_ID]["expires"] = str(self.expires)

	def __getitem__(self, item):
		"""Get the item from the session"""
		if not self.started:
			raise NotStarted("Session must be started")
		return self.data.__getitem__(item)

	def __setitem__(self, item, value):
		"""set the item into the session"""
		if not self.started:
			raise NotStarted("Session must be started")
		self.data.__setitem__(item, value)

	def __delitem__(self, item):
		if not self.started:
			raise NotStarted("Session must be started")
		self.data.__delitem__(item)

	def __contains__(self, item):
		"""Return if item in the session"""
		if not self.started:
			raise NotStarted("Session must be started")
		return self.data.__contains__(item)

	def __iter__(self):
		"""Go through the names of all the session variables"""
		if not self.started:
			raise NotStarted("Session must be started")
		return self.data.__iter__()

def start():
	SESSION = get_session()
	if not SESSION.started:
		return SESSION.start()
	else:
		return True

def destroy():
	global SESSION
	if SESSION:
		SESSION.destroy()

def get_session():
	global SESSION
	if not SESSION:
		SESSION = Session()
	return SESSION

### The following is a (little) modified version of this:
# http://www.evanfosmark.com/2009/01/cross-platform-file-locking-support-in-python/

class FileLockException(Exception):
	pass

class FileLock(object):
	""" A file locking mechanism that has context-manager support so
		you can use it in a with statement. This should be relatively cross
		compatible as it doesn't rely on msvcrt or fcntl for the locking.
	"""

	def __init__(self, file_name, timeout=10, delay=.05):
		""" Prepare the file locker. Specify the file to lock and optionally
			the maximum timeout and the delay between each attempt to lock.
		"""
		self.is_locked = False
		self.lockfile = os.path.join(os.getcwd(), "%s.lock" % file_name)
		self.file_name = file_name
		self.timeout = timeout
		self.delay = delay

	def acquire(self):
		""" Acquire the lock, if possible. If the lock is in use, it check again
			every `wait` seconds. It does this until it either gets the lock or
			exceeds `timeout` number of seconds, in which case it throws
			an exception.
		"""
		if self.is_locked:
			return

		start_time = time.time()
		while True:
			try:
				self.fd = os.open(self.lockfile, os.O_CREAT|os.O_EXCL|os.O_RDWR)
				break;
			except OSError as e:
				if e.errno != errno.EEXIST:
					raise

				if (time.time() - start_time) >= self.timeout:
					raise FileLockException("Timeout occured.")
				time.sleep(self.delay)
		self.is_locked = True

	def release(self):
		""" Get rid of the lock by deleting the lockfile.
			When working in a `with` statement, this gets automatically
			called at the end.
		"""
		if self.is_locked:
			os.close(self.fd)
			os.unlink(self.lockfile)
			self.is_locked = False

	def __enter__(self):
		""" Activated when used in the with statement.
			Should automatically acquire a lock to be used in the with block.
		"""
		if not self.is_locked:
			self.acquire()
		return self

	def __exit__(self, type, value, traceback):
		""" Activated at the end of the with statement.
			It automatically releases the lock if it isn't locked.
		"""
		if self.is_locked:
			self.release()

	def __del__(self):
		""" Make sure that the FileLock instance doesn't leave a lockfile
			lying around.
		"""
		self.release()

def print_session(session):
	"""
	Prints info from the current session.

	WARNING: ONLY FOR DEBUGGING. MAJOR SECURITY RISK!
	"""
	print("<h3>Session Data</h3>")
	print("<dl>")
	for name in session:
		print("<dt>%s <i>%s</i></dt>"%(name, type(session[name])))
		print("<dd>%s</dd>"%repr(session[name]))
	print("</dl>")


start()

		