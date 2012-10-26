"""
RandomMessagePlugin by caske33

config:
	message-threshold = number of messages that must be sent between random messages
	delay-minutes = number of minutes between messages
	message-file [default: messages.txt] = file with messages, one per line 
"""

import os, random

import chatlib

class RandomMessagePlugin(chatlib.Plugin):
	def __init__(self, bot):
		super(type(self), self).__init__(bot)
		self.setIdleTimer(60.0*int(self.getConfig('delay-minutes')))
		self.messageThreshold = int(self.getConfig('message-threshold', 5))
		self.messageCount = dict()

	def handleChat(self, chan, sender, msg):
		if chan not in self.messageCount:
			self.messageCount[chan] = 0
		self.messageCount[chan] += 1
		return True

	def idle(self):
		for chan,count in self.messageCount.items():
			if count < self.messageThreshold: continue
			with open(self.getConfig('message-file', 'messages.txt'), 'r') as f:
				self.bot.say(chan, random.choice([x.strip() for x in f.readlines() if len(x.strip())]))
			self.messageCount[chan] = 0
