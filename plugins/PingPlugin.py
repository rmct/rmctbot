"""
PingPlugin by authorblues

config: none
"""

import pyirc.Plugin

class PingPlugin(pyirc.Plugin.Plugin):
	def handleCommand(self, chan, sender, cmd, args):
		if cmd == 'ping':
			self.bot.sayTo(chan, sender, 'Pong!')
		return True

