"""
LearningPlugin by authorblues

config:
	database-file = location for sqlite database
"""

import sqlite3

import chatlib

class LearningPlugin(chatlib.Plugin):
	def __init__(self, bot):
		super(type(self), self).__init__(bot, priority=self.PRIORITY_LOW)
		print(self.getConfig('database-file'))
		self.conn = sqlite3.connect(self.getConfig('database-file'))
		self.conn.execute('''
			CREATE TABLE IF NOT EXISTS Commands (
			  command_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
			  command TEXT UNIQUE NOT NULL,
			  text TEXT NOT NULL,
			  creator TEXT NOT NULL
			);
		''')

	def handleCommand(self, chan, sender, cmd, args):
		if cmd == 'learn' and len(args) == 2:
			newcmd, text = args
			self.conn.execute('INSERT INTO Commands(command, text, creator) VALUES(?, ?, ?)', (newcmd.lower(), text, sender))
			self.conn.commit()
			return True

		else:
			target = sender
			for i,x in enumerate(args):
				if x.startswith('~'):
					target = x[1:]
					del args[i]

			c = self.conn.cursor()
			c.execute('SELECT text FROM Commands WHERE command = ?', (cmd.lower(), ))

			row = c.fetchone()
			c.close()

			if row is None: return False
			text, = row
			self.bot.sayTo(chan, target, text % tuple(args))
			return True
