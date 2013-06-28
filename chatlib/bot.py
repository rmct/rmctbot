import os, sys
import socket, select
import shlex
import time
import ConfigParser
import operator

import re
import chatlib

from collections import deque

def messagehandler(*typelist):
	def func(f):
		f.msgtypes = typelist
		return f
	return func

class Bot:
	def changeNick(self, nick):
		self.send('NICK {nick:s}'.format(nick=nick))
		self.nick = nick
		return self

	def getName(self):
		return self.nick

	def getHost(self):
		return self.host

	def join(self, *chans):
		for chan in chans:
			if chan not in self.joinq:
				self.joinq.append(chan)
		return self

	def invite(self, chan, nick):
		self._sendImmediate('INVITE {0:s} {1:s}'.format(nick, chan))
		return self

	def part(self, *chans):
		for chan in chans:
			self.send('PART {0:s}'.format(chan))
			del self.channels[chan]
		return self

	def quit(self, reason=None):
		rtext = '' if reason is None else ':{0:s}'.format(reason)
		self._sendImmediate('QUIT {0:s}'.format(rtext).strip())
		return self

	def send(self, msg):
		self.mbfr.append(msg)
		return self

	def _sendImmediate(self, msg):
		if self.debug: print('\r<-- {0:s}'.format(msg))
		self.conn.send((msg + '\r\n').encode('utf8'))

	def say(self, recp, msg):
		self.send('PRIVMSG {recp:s} :{msg:s}'.format(recp=recp, msg=msg))
		for p in self.plugins:
			p.handleChat(recp, self.nick, msg)
		return self

	def sayTo(self, recp, target, msg):
		self.say(recp, '{0:s}: {1:s}'.format(target, msg))
		return self

	def sayAll(self, msg):
		for chan in self.getChannels():
			self.say(chan, msg)
		return self

	def getChannels(self):
		return self.channels.keys()

	def isUserOp(self, chan, user):
		if chan not in self.channels: return False
		if user not in self.channels[chan].users: return False
		return 'o' in self.channels[chan].users[user]

	def isUserVoiced(self, chan, user):
		if chan not in self.channels: return False
		if user not in self.channels[chan].users: return False
		return any(x in self.channels[chan].users[user] for x in frozenset('vo'))

	def __init__(self, nick, host, port=6667, passwd=None, real=None, debug=False):
		self.mbfr = deque()
		self.joinq = deque()
		self.debug = debug

		self.connected = False
		self.authenticated = False
		self.hostmasked = (passwd is None)

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

		self.send('PASS {passwd:s}'.format(passwd=passwd))
		self.changeNick(nick)
		self.send('USER {nick:s} {host:s} * :{real:s}'.format(nick=self.nick, host=host, real=self.real))

		self.plugins = []
		self.channels = dict()
		self.registerMessageHandlers()
		self.config = ConfigParser.SafeConfigParser()

	def registerMessageHandlers(self):
		self.handlers = dict()
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
				self.say('nickserv', 'IDENTIFY {passwd:s}'.format(**params))
				self.say('nickserv', 'GHOST {nick:s} {passwd:s}'.format(**params))
		self.authenticated = True
		return self

	def loadConfig(self, *filenames):
		self.config.read(*filenames)
		return self

	def loadPlugins(self, path):
		for root, dirs, files in os.walk(path):
			for name in files:
				if name.endswith('.py') and not name.startswith('__'):
					path = os.path.relpath(os.path.join(root, name))
					mname = path[:-3].replace(os.sep, '.')

					mod = __import__(mname).__dict__
					for v in mname.split('.')[1:]:
						mod = mod[v].__dict__
					for p in mod.values():
						if type(p) == type and issubclass(p, chatlib.Plugin):
							self.addPlugin(p(self))
		return self

	def addPlugin(self, plugin):
		print('* Loading {0:s}'.format(plugin.getPluginName()))
		self.plugins.append(plugin)
		self.plugins.sort(key=operator.attrgetter('priority'))

	def listen(self):
		try:
			while True:
				# if any messages are ready to be listened to, listen to them
				rlist, wlist, xlist = select.select([self.conn], [], [], 0.1)
				for r in rlist: self.read(r)

				if self.connected:
					if not self.authenticated:
						self.authenticate()
					while self.hostmasked and len(self.joinq):
						chan = self.joinq.popleft()
				
						if chan not in self.channels.values():
							self.send('JOIN {chan:s}'.format(chan=chan))

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
			self.handle(Message(m))
	   
	def handle(self, msg):
		if self.debug: print('\r--> {0:s}'.format(msg))

		if msg.isPing():
			self._sendImmediate(msg.getPong())
		elif msg.msgtype in self.handlers:
			body = msg.getMessageText()
			chan, nick, subnet = msg.getDelivery()

			# call the appropriate message handler
			self.handlers[msg.msgtype](msg, body, chan, nick, subnet)

	@messagehandler('PRIVMSG')
	def msg_PRIVMSG(self, msg, body, chan, nick, subnet):
		if body.startswith("\u0001ACTION") and body.endswith("\u0001"):
			body = body[8:-1]
			for p in self.plugins:
				p.handleAction(chan, nick, body)
		else:
			for p in self.plugins:
				p.handleChat(chan, nick, body)

		if body.startswith(Message.commandChar):
			#cmd, *args = shlex.split(body[1:])
			args = shlex.split(body[1:])
			for p in self.plugins:
				p.handleCommand(chan, nick, args[0], args[1:])

	@messagehandler('JOIN')
	def msg_JOIN(self, msg, body, chan, nick, subnet):
		if nick == self.nick:
			print('Joining {0:s}'.format(chan))
			self.channels[chan] = Bot.Channel(chan)
		if chan in self.channels:
			self.channels[chan].users[nick] = set() # TODO
		for p in self.plugins:
			p.onChannelJoin(chan, nick)

	@messagehandler('PART')
	def msg_PART(self, msg, body, chan, nick, subnet):
		if chan in self.channels:
			del self.channels[chan].users[nick]
			if nick == self.nick:
				del self.channels[chan]
		for p in self.plugins:
			p.onChannelPart(chan, nick)

	@messagehandler('QUIT')
	def msg_QUIT(self, msg, body, chan, nick, subnet):
		for p in self.plugins:
			p.onQuit(nick, reason=body)

	@messagehandler('NICK')
	def msg_NICK(self, msg, body, chan, nick, subnet):
		oldnick, newnick = nick, body
		for p in self.plugins:
			p.onNickChange(oldnick, newnick)
		for chan,cinfo in self.channels.items():
			if oldnick in cinfo.users:
				cinfo.users[newnick] = cinfo.users[oldnick]
				del cinfo.users[oldnick]

	@messagehandler('KICK')
	def msg_KICK(self, msg, body, chan, nick, subnet):
		for p in self.plugins:
			p.onKick(chan, msg.get(3), reason=body)

	@messagehandler('INVITE')
	def msg_INVITE(self, msg, body, chan, nick, subnet):
		if self.nick == msg.get(2):
			for p in self.plugins:
				p.onInvite(msg.get(3))

	@messagehandler('MODE')
	def msg_MODE(self, msg, body, chan, nick, subnet):
		mode = msg.get(3)
		target = msg.get(2)

		user = msg.get(4)
		if target.startswith('#') and user is not None:
			flags = set(mode[1:])

			if 'user' not in self.channels[target].users[user]: return
			uflags = self.channels[target].users[user]
			if mode.startswith('-'): uflags = uflags - flags
			if mode.startswith('+'): uflags = uflags | flags
			self.channels[target].users[user] = uflags

		if target == self.nick:
			if mode == '+x': self.hostmasked = True

	@messagehandler('NOTICE')
	def msg_NOTICE(self, msg, body, chan, nick, subnet):
		pass

	@messagehandler('001')
	def msg_connect(self, msg, body, chan, nick, subnet):
		print('Connection established.')
		self._sendImmediate('MODE {0:s} +x'.format(self.nick))
		self.connected = True

	@messagehandler('353')
	def msg_names(self, msg, body, chan, nick, subnet):
		if chan not in self.channels: return
		chaninfo = self.channels[chan]

		for name in body.strip().split():
			flags = set(name) & set('@+')
			name = name.lstrip('@+')
			chaninfo.users[name] = convertflags(flags)

			#self.say('chanserv', 'FLAGS {0:s} {1:s}'.format(chan, name))
	
	@messagehandler('396')
	def msg_hostmask(self, msg, body, chan, nick, subnet):
		self.hostmasked = True

	class Channel:
		def __init__(self, chan):
			self.name = chan
			self.users = dict()

		def __hash__(self):
			return hash(self.name)

flagtable = {
	'@': 'o',
	'+': 'v',
}

def convertflags(flagset):
	newset = set()
	for x in flagset:
		newset.add(flagtable[x] if x in flagtable else x)
	return newset
	return

class Message:
	commandChar = '!'

	deliveryParser = re.compile('^:([^ !]+?)!([^ ]+?)$', re.I)
	channelFinder = re.compile('(#[^ ]+)', re.I)

	def get(self, n):
		if self.msg is None: return None
		parts = self.msg.split(None, n + 1)
		return parts[n] if n < len(parts) else None

	def __init__(self, m):
		self.msg = m
		self.msgtype = self.get(1)

	def __str__(self):
		return self.msg.encode('utf8', 'replace')

	def isPing(self):
		return self.msg.startswith('PING')

	def getPong(self):
		if not self.isPing(): return None
		return 'PONG' + self.msg[4:]

	def isChat(self):
		return self.msgtype == 'PRIVMSG'

	def getMessageText(self):
		if ' :' not in self.msg: return None
		return self.msg.split(' :', 1)[1].strip()

	def isCommand(self):
		body = self.getMessageBody()
		return body is not None and body.startswith(Message.commandChar)

	def getNick(self):
		parse = Message.deliveryParser.search(self.get(0))
		return None if parse is None else parse.group(1).strip()

	def getSubnet(self):
		parse = Message.deliveryParser.search(self.get(0))
		return None if parse is None else parse.group(2).strip()

	def getChannel(self):
		csearch = Message.channelFinder.search(self.msg)
		return None if csearch is None else csearch.group(1).strip()

	def getDelivery(self):
		return self.getChannel(), self.getNick(), self.getSubnet() 

