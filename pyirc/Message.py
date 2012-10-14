import re

class Message:
	commandChar = '!'
	deliveryParser = re.compile("^:([^ !]+?)!([^ ]+?)$", re.I)

	def get(self, n):
		if self.msg is None: return None
		parts = self.msg.split(None, n + 1)
		return parts[n] if n < len(parts) else None

	def __init__(self, m):
		self.msg = m
		self.msgtype = self.get(1)

	def __str__(self):
		return self.msg

	def isPing(self):
		return self.msg.startswith('PING')

	def getPong(self):
		if not self.isPing(): return None
		return 'PONG' + self.msg[4:]

	def isChat(self):
		return self.msgtype == 'PRIVMSG'

	def getMessageText(self):
		if ' :' not in self.msg: return None
		return self.msg.split(' :', 1)[1]

	def isCommand(self):
		body = self.getMessageBody()
		return body is not None and body.startswith(Message.commandChar)

	def getNick(self):
		parse = Message.deliveryParser.search(self.get(0))
		return None if parse is None else parse.group(1)

	def getSubnet(self):
		parse = Message.deliveryParser.search(self.get(0))
		return None if parse is None else parse.group(2)

	def getChannel(self):
		return self.get(2)

	def getDelivery(self):
		return self.getChannel(), self.getNick(), self.getSubnet() 
