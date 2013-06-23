"""
PugPlugin by authorblues

config:
	delay-minutes = number of minutes between PUG updates
	server-address = address running AutoReferee for players to connect
"""

import time
import chatlib

class PugPlugin(chatlib.Plugin):
	IGNORED_USERS = set(['ChanServ'])
	HELP_TEXT = """
		!help - See help for PUG plugin
		!map <name> - Select a map for the PUG
		!maplist - Print list of available maps
		!size <n> - Set number of players per team
		!lock - Only PUG creator may set settings
	"""

	def __init__(self, bot):
		super(type(self), self).__init__(bot, priority=self.PRIORITY_HIGH)
		self.setIdleTimer(60.0 * int(self.getConfig('delay-minutes', default=3)))
		self.pugchannels = dict()
	
	def handleCommand(self, chan, sender, cmd, args):
		if chan not in self.pugchannels:
			if cmd == 'pug':
				room = '#rmct-{0:x}'.format(int(time.time()) % (1 << 32))
				pugchan = PugPlugin.PugChannel(room, sender)

				self.bot.join(room)
				for name in args:
					if name in self.bot.channels[chan].users:
						pugchan.invite.add(name)
				self.pugchannels[room] = pugchan
				return True

		if chan in self.pugchannels:
			pugchan = self.pugchannels[chan]
			if cmd == 'help':
				self.sendHelp(chan)

			elif cmd == 'lock' and sender == pugchan.creator:
				pugchan.lock = not pugchan.lock
				if pugchan.lock:
					self.bot.say(chan, 'Only ' + pugchan.creator + ' may change PUG settings')
				else: self.bot.say(chan, 'Anyone may change PUG settings')

			elif cmd == 'size' and pugchan.canEdit(sender):
				pugchan.size = int(args[0]) * 2

			elif cmd == 'map' and pugchan.canEdit(sender):
				newmap = self.getMap(''.join(args))
				self.bot.say(chan, 'The map has been set to ' + newmap)
				pugchan.mapname = newmap

	def idle(self):
		pass

	def getMap(self, mapname):
		return mapname

	def onChannelJoin(self, chan, nick):
		if nick == self.bot.nick and chan in self.pugchannels:
			for name in self.pugchannels[chan].invite:
				self.bot.invite(chan=chan, nick=name)
			self.pugchannels[chan].invite = set()
		if chan in self.pugchannels and nick == self.pugchannels[chan].creator:
			self.bot.say(chan, 'Welcome to RMCT PUG room ' + chan)
			self.bot.say(chan, 'Invite users to this room to organize your game')
			self.sendHelp(chan)

	def sendHelp(self, chan):
		for line in PugPlugin.HELP_TEXT.splitlines():
			line = line.strip()
			if len(line): self.bot.say(chan, line)


	def userchange(self, chan):
		if chan not in self.bot.channels:
			return True

		users = self.bot.channels[chan].users.keys()
		users = set(users) - PugPlugin.IGNORED_USERS - set([self.bot.getName()])

		if chan in self.pugchannels and not len(users):
			self.bot.part(chan)

	def onChannelPart(self, chan, nick):
		self.userchange(chan)

	def onQuit(self, nick, reason):
		for chan in self.bot.channels:
			if nick in self.bot.channels[chan].users:
				self.userchange(chan)

	def onKick(self, chan, nick, reason):
		self.userchange(chan)

	class PugChannel:
		def __init__(self, chan, creator):
			self.chan = chan
			self.creator = creator
			self.lock = False

			self.invite = set()
			self.invite.add(creator)

			self.size = 4
			self.gamemap = None

		def canEdit(self, nick):
			return not self.lock or nick == self.creator

