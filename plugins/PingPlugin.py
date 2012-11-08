"""
PingPlugin by authorblues

config: none
"""

import chatlib

class PingPlugin(chatlib.Plugin):
	def handleCommand(self, chan, sender, cmd, args):
		if cmd == 'ping':
			self.bot.sayTo(chan, sender, 'Pong!')
			return True

