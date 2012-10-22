"""
OperatorPlugin by authorblues

config: none
"""

import chatlib

class OperatorPlugin(chatlib.Plugin):
	def handleCommand(self, chan, sender, cmd, args):
		return True

