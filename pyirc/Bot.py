# adapted from github.com/epw/pyirc
import os, sys
import imp
import socket, select
import shlex
import time

from collections import deque

import pyirc.Message, pyirc.Plugin

def messageHandler(*typelist):
	def func(f):
		f.msgtypes = typelist
		return f
	return func

class Bot:
	def changeNick(self, nick):
		self.send('NICK {nick:s}'.format(nick=nick))
		self.nick = nick
		return self

	def join(self, *chans):
		for chan in chans:
			self.joinq.append(chan)
		return self

	def part(self, *chans):
		for chan in chans:
			self.send('PART {:s}'.format(chan))
			del self.channels[chan]
		return self

	def quit(self, reason=None):
		rtext = '' if reason is None else ':{:s}'.format(reason)
		self._sendImmediate('QUIT {:s}'.format(rtext).strip())
		return self

	def send(self, msg):
		self.mbfr.append(msg)
		return self

	def _sendImmediate(self, msg):
		if self.debug: print('\r<-- {:s}'.format(msg))
		self.conn.send((msg + '\r\n').encode('utf8'))

	def say(self, recp, msg):
		self.send('PRIVMSG {recp:s} :{msg:s}'.format(recp=recp, msg=msg))
		for p in self.plugins:
			p.handleChat(recp, self.nick, msg)
		return self

	def sayTo(self, recp, target, msg):
		self.say(recp, '{:s}: {:s}'.format(target, msg))
		return self

	def sayAll(self, msg):
		for chan in self.getChannels():
			self.say(chan, msg)
		return self

	def getChannels(self):
		return self.channels.keys()

	def __init__(self, nick, host, port=6667, passwd=None, real=None, debug=False):
		self.mbfr = deque()
		self.joinq = deque()
		self.debug = debug

		self.connected = False
		self.authenticated = False

		self.host, self.port, self.conn = host, port, None
		while self.conn is None:
			try:
				print('Creating connection...')
				self.conn = socket.create_connection((host, port), 0.5)
			except socket.timeout as e:
				self.conn = None

		self.conn.setblocking(0)

		self.real = real if real is not None else nick
		self.passwd = passwd

		self.send('PASS {passwd:s}'.format(passwd=passwd)).changeNick(nick)
		self.send('USER {nick:s} {host:s} * :{real:s}'.format(nick=nick, host=host, real=real))

		self.channels = {}
		self.plugins = set()
		self.registerMessageHandlers()

	def registerMessageHandlers(self):
		self.handlers = {}
		for func in dir(self):
			f = getattr(self, func)
			if hasattr(f, 'msgtypes'):
				for t in f.msgtypes:
					self.handlers[t] = f

	def authenticate(self):
		if self.passwd is not None:
			params = {'nick': self.nick, 'passwd': self.passwd}
			if 'quakenet' in self.host:
				self.say('Q@CServe.quakenet.org', 'AUTH {nick:s} {passwd:s}'.format(**params))
			elif 'gamesurge' in self.host:
				self.say('AuthServ@Services.GameSurge.net', 'AUTH {nick:s} {passwd:s}'.format(**params))
			else:
				self.say('nickserv', 'GHOST {nick:s} {passwd:s}'.format(**params))
		self.authenticated = True
		return self

	def loadPlugins(self, path):
		for root, dirs, files in os.walk(path):
			for name in files:
				if name.endswith('.py') and not name.startswith('__'):
					path = os.path.relpath(os.path.join(root, name))
					mname = path[:-3].replace('/', '.')

					mod = __import__(mname).__dict__
					for v in mname.split('.')[1:]:
						mod = mod[v].__dict__
					for p in mod.values():
						if type(p) == type and issubclass(p, pyirc.Plugin.Plugin):
							self.addPlugin(p(self))
		return self

	def addPlugin(self, plugin):
		print('* Loading {:s}'.format(plugin.getPluginName()))
		self.plugins.add(plugin)

	def listen(self):
		try:
			while True:
				# if any messages are ready to be listened to, listen to them
				rlist, wlist, xlist = select.select([self.conn], [], [], 0.1)
				for r in rlist: self.read(r)

				if self.connected:
					if not self.authenticated:
						self.authenticate()
					while len(self.joinq):
						chan = self.joinq.popleft()
				
						if chan not in self.channels.values():
							self.send('JOIN {chan:s}'.format(chan=chan))
							self.channels[chan] = Bot.Channel(chan)

					clock = time.time()
					for p in self.plugins:
						if p.idledelay is not None and clock > p.idleclock + p.idledelay:
							p.idleclock = clock
							p.idle()

				# send queued messages
				while len(self.mbfr):
					self._sendImmediate(self.mbfr.popleft())

		# don't make a bit fuss about exiting
		except (KeyboardInterrupt, SystemExit) as e:
			self.quit(reason='Exiting')

	def read(self, conn):
		msg = ''
		try:
			while True: msg += conn.recv(1024).decode('utf8')
		except Exception as e: pass

		for m in msg.rstrip().split('\n'):
			self.handle(pyirc.Message.Message(m))
	   
	def handle(self, msg):
		if self.debug: print('\r--> {:s}'.format(msg))

		if msg.isPing():
			self._sendImmediate(msg.getPong())
		elif msg.msgtype in self.handlers:
			body = msg.getMessageText()
			chan, nick, subnet = msg.getDelivery()

			# call the appropriate message handler
			self.handlers[msg.msgtype](msg, body, chan, nick, subnet)

	@messageHandler('PRIVMSG')
	def msg_PRIVMSG(self, msg, body, chan, nick, subnet):
		if body.startswith("\u0001ACTION") and body.endswith("\u0001"):
			body = body[8:-1]
			for p in self.plugins:
				p.handleAction(chan, nick, body)
		else:
			for p in self.plugins:
				p.handleChat(chan, nick, body)

		if body.startswith(pyirc.Message.Message.commandChar):
			cmd, *args = shlex.split(body[1:])
			for p in self.plugins:
				p.handleCommand(chan, nick, cmd, args)

	@messageHandler('JOIN')
	def msg_JOIN(self, msg, body, chan, nick, subnet):
		if chan in self.channels:
			self.channels[chan].users[nick] = set() # TODO
		for p in self.plugins:
			p.onChannelJoin(chan, nick)

	@messageHandler('PART')
	def msg_PART(self, msg, body, chan, nick, subnet):
		if chan in self.channels:
			del self.channels[chan].users[nick]
		for p in self.plugins:
			p.onChannelPart(chan, nick)

	@messageHandler('QUIT')
	def msg_QUIT(self, msg, body, chan, nick, subnet):
		for p in self.plugins:
			p.onQuit(nick, reason=body)

	@messageHandler('NICK')
	def msg_NICK(self, msg, body, chan, nick, subnet):
		oldnick, newnick = nick, body
		print('nick change', oldnick, newnick)
		for p in self.plugins:
			p.onNickChange(oldnick, newnick)
		for chan,cinfo in self.channels.items():
			if oldnick in cinfo.users:
				cinfo.users[newnick] = cinfo.users[oldnick]
				del cinfo.users[oldnick]

	@messageHandler('KICK')
	def msg_KICK(self, msg, body, chan, nick, subnet):
		for p in self.plugins:
			p.onQuit(chan, msg.get(3), reason=body)

	@messageHandler('INVITE')
	def msg_INVITE(self, msg, body, chan, nick, subnet):
		if self.nick == msg.get(2):
			for p in self.plugins:
				p.onInvite(msg.get(3))
			
	@messageHandler('001')
	def msg_connect(self, msg, body, chan, nick, subnet):
		print('Connection established.')
		self._sendImmediate('MODE {:s} +x'.format(self.nick))
		self.connected = True

	@messageHandler('353')
	def msg_names(self, msg, body, chan, nick, subnet):
		if chan not in self.channels: return
		chaninfo = self.channels[chan]

		for name in body.strip().split():
			flags = set() # TODO
			name = name.lstrip('@+')
			chaninfo.users[name] = flags

	class Channel:
		def __init__(self, chan):
			self.name = chan
			self.users = dict()

		def __hash__(self):
			return hash(self.name)
		
