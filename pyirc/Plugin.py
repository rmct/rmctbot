import time, datetime

class Plugin:
	def __init__(self, bot):
		self.idledelay = None
		self.bot = bot
	
	def handleChat(self, chan, sender, msg):
		return False
	
	def handleAction(self, chan, sender, msg):
		return self.handleChat(chan, sender, msg)

	def handlePrivateMessage(self, sender, msg):
		return self.handleChat(sender, sender, msg)

	def handleCommand(self, chan, sender, cmd, args):
		return False

	def onChannelJoin(self, chan, nick):
		return False

	def onChannelPart(self, chan, nick):
		return False

	def onQuit(self, nick, reason=None):
		return False

	def onInvite(self, chan):
		return False

	def onKick(self, chan, nick, reason=None):
		return False

	def onNickChange(self, oldnick, newnick):
		return False

	def onModeChange(self, chan, nick):
		return False

	def idle(self):
		return False

	def setIdleTimer(self, sec=None):
		self.idledelay = sec
		self.idleclock = time.time()

	def getPluginName(self):
		return self.__class__.__name__

	def getConfig(self, option, default=None):
		if self.bot.config is None or not self.bot.config.has_option(self.getPluginName(), option):
			return default
		return self.bot.config.get(self.getPluginName(), option)

	def getConfigOptions(self):
		if self.bot.config is not None and self.bot.config.has_section(self.getPluginName()):
			return self.bot.config.options(self.getPluginName())
		return []

	def isUserOp(self, chan, user):
		return self.bot.isUserOp(chan, user)

	def isUserVoiced(self, chan, user):
		return self.bot.isUserVoiced(chan, user)

	def log(self, message):
		now = datetime.datetime.now()
		now -= datetime.timedelta(microseconds=now.microsecond)
		print('[{:s}] <{:s}> {:s}'.format(str(now), self.getPluginName(), message))
