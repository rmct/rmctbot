"""
OperatorPlugin by authorblues

config: none
"""

import pyirc.Plugin

class OperatorPlugin(pyirc.Plugin.Plugin):
	def handleCommand(self, chan, sender, cmd, args):
		if cmd == 'getmode' and len(args) == 1:
			who, = args
			flags = ' '.join(self.bot.channels[chan].users[who])
			self.bot.sayTo(chan, sender, "{:s}'s mode is {:s}".format(who, flags))
		return True

