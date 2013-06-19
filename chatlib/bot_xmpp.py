import os, sys
import shlex
import time
import ConfigParser
import operator

import xmpp
import chatlib

from collections import deque

class Bot(object):
	cmdToken = '!'
	broadcast_channel = 'broadcast'

	def changeNick(self, nick):
		return self

	def getName(self):
		return self.jid.getNode()

	def getHost(self):
		return self.jid.getDomain()

	def join(self, *chans):
		nick = self.getName()
		for chan in chans:
			p = xmpp.protocol.Presence(to='{0:s}/{1:s}'.format(chan, nick))
			p.setTag('x', namespace=xmpp.protocol.NS_MUC)
			p.getTag('x').addChild('history', {'maxchars': '0','maxstanzas': '0'})
			self.conn.send(p)
			self.channels[chan] = None
		return self

	def say(self, recp, msg):
		message = xmpp.protocol.Message(recp, msg)
		if recp in self.channels:
			message.setType('groupchat')
		self.conn.send(message)
		return self

	def broadcast(self, msg, host=None, group='all'):
		if host is None: host = self.getHost()
		return self.say('{0:s}@{1:s}.{2:s}'.format(group, self.broadcast_channel, host), msg)

	def sayTo(self, recp, target, msg):
		self.say(recp, '{0:s}: {1:s}'.format(target, msg))
		return self

	def sayAll(self, msg):
		for chan in self.channels.keys():
			self.say(chan, msg)
		return self

	def getChannels(self):
		return self.channels.keys()

	def __init__(self, jid, passwd=None, debug=False):
		self.debug = debug
		if type(jid) is not xmpp.protocol.JID:
			jid = xmpp.protocol.JID(jid)
		self.jid = jid

		xdebug = ['dispatcher', 'bind', 'socket', 'TLS', 'roster'] if debug else []
		self.conn = conn = xmpp.Client(jid.getDomain(), debug=xdebug)
		assert conn.connect() is not None

		conn.RegisterHandler('message', self.handleMessage)
		conn.RegisterHandler('presence', self.handlePresence)
		conn.RegisterHandler('iq', self.handleIq)

		conn.auth(jid.getNode(), passwd, sasl=0, resource=jid.getResource())
		conn.sendInitPresence()

		self.plugins = []
		self.channels = dict()
		self.config = ConfigParser.SafeConfigParser()

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

	def handleMessage(self, session, msg):
		mfrom = msg.getFrom()
		mtext = msg.getBody()
		if mtext is None: return

		recp = mfrom.getStripped()
		nick = mfrom.getResource()

		if msg.getType() == 'chat':
			nick = mfrom.getNode()

		for p in self.plugins:
			if p.handleChat(recp, nick, mtext): break

		if mtext.startswith(self.cmdToken):
			parts = shlex.split(mtext.encode('utf8').strip())
			cmd, args = parts[0][1:], parts[1:]

			for p in self.plugins:
				if p.handleCommand(recp, nick, cmd, args): break

	def handlePresence(self, session, pres):
		nick = pres.getFrom().getResource()
		if pres.getType() == 'unavailable':
			pass

	def handleIq(self, session, iq):
		reply = iq.buildReply('result')
		session.send(reply)
		raise xmpp.protocol.NodeProcessed

	def listen(self):
		while True:
			clock = time.time()
			for p in self.plugins:
				if p.idledelay is not None and clock > p.idleclock + p.idledelay:
					p.idleclock = clock
					p.idle()
			self.conn.Process(1)
		return

