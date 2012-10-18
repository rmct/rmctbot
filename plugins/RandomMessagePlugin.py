"""
RandomMessagePlugin by caske33

config:
	message-threshold = number of messages that must be sent between random messages
	delay-minutes = number of minutes between messages
	message-file [default: messages.txt] = file with messages, one per line 
"""

import os, random

import pyirc.Plugin

class RandomMessagePlugin(pyirc.Plugin.Plugin):
	def __init__(self, bot):
		super().__init__(bot)
		self.setIdleTimer(60.0*int(self.getConfig('delay-minutes')))
		self.messageThreshold = int(self.getConfig('message-threshold', 5))
		self.messageCount = 0

	def handleChat(self, chan, sender, msg):
		self.messageCount += 1

	def idle(self):
		if self.messageCount < self.messageThreshold: return
		self.messageCount = 0
		with open(self.getConfig('message-file', 'messages.txt'), 'r') as f:
			messages = [x.strip() for x in f.readlines() if len(x.strip())]
			self.bot.sayAll(random.choice(messages))
