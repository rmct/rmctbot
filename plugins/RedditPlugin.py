"""
RedditPlugin by authorblues

config:
	subreddits = a comma-seperated list of subreddits to monitor
	delay-minutes = number of minutes between updates
"""

import urllib2, json

import chatlib

class RedditPlugin(chatlib.Plugin):
	def __init__(self, bot):
		super(type(self), self).__init__(bot)
		self.setIdleTimer(60.0 * int(self.getConfig('delay-minutes')))
		self.lastid = None

		self.subs = self.getConfig('subreddits').split(',')
		self.req = urllib2.Request('http://www.reddit.com/r/{0:s}/new.json?limit=5'.format('+'.join(self.subs)),
			headers = {'User-Agent': '{0:s}@{1:s} -- github.com/rmct/rmctbot'.format(self.bot.getName(), self.bot.getHost())})

	def idle(self):
		try:
			feed = json.loads(urllib2.urlopen(self.req).read())
			if feed is not None:
				try:
					entries = feed['data']['children']
					if self.lastid is not None:
						for entry in entries:
							if self.lastid == entry['data']['id']: break
							if len(entry['data']['title']) > 60:
								entry['data']['title'] = entry['data']['title'][:57] + '...'
							self.bot.sayAll(('r/{subreddit:s} : "{title:s}" by {author:s} ' + 
								'-- http://redd.it/{id:s}').format(**entry['data']))
				
					if len(entries):
						self.lastid = entries[0]['data']['id']

					# this is a hack :)
					if self.lastid is None:
						self.lastid = '#'
				except KeyError as e:
					pass
		except urllib2.HTTPError as e:
			pass
		return True

