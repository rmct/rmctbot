"""
RandomMessagePlugin by caske33

config:
	delay-minutes = number of minutes between messages
    message-file [default: messages.txt] = file with messages, one per line 
"""

import os, random

import pyirc.Plugin

class RandomMessagePlugin(pyirc.Plugin.Plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.setIdleTimer(60.0*int(self.getConfig('delay-minutes')))

    def idle(self):
        with open(self.getConfig('message-file', 'messages.txt'), 'r') as f:
            self.bot.sayAll(random.choice(f.readlines()))
