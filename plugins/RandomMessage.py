#Random Message plugin by caske33. Displays a random message every so often.
import os,random

import pyirc.Plugin

class RandomMessagePlugin(pyirc.Plugin.Plugin):
    messages = [""]
    

    def __init__(self, bot):
        super().__init__(bot)
        self.setIdleTimer(60.0*30)

        f = open('plugins/messages.txt', 'r')
        for line in f.readlines():
            self.messages.append(line)

    def idle(self):
        self.bot.sayAll(self.messages[random.randint(0,len(self.messages) - 1)])
