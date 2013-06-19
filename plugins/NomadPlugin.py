"""
NomadPlugin by authorblues

config: none
"""

import chatlib

class NomadPlugin(chatlib.Plugin):
	def onInvite(self, chan):
		self.bot.join(chan)

