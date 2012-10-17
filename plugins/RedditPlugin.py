import urllib.request, urllib.error, json

import pyirc.Plugin

class RedditPlugin(pyirc.Plugin.Plugin):
	subs = ['mctourney', 'championsofthemap']

	def __init__(self, bot):
		super().__init__(bot)
		self.setIdleTimer(10.0)
		self.lastid = None

		self.req = urllib.request.Request('http://www.reddit.com/r/{:s}/new.json?limit=5'.format('+'.join(self.subs)),
			headers = {'User-Agent': '{:s}@{:s} -- github.com/rmct/rmctbot'.format(self.bot.real, self.bot.host)})

	def idle(self):
		try:
			feed = json.loads(urllib.request.urlopen(self.req).read().decode('utf8'))
			if feed is not None:
				try:
					entries = feed['data']['children']
					if self.lastid is not None:
						for entry in entries:
							if self.lastid == entry['data']['id']: break
							if len(entry['data']['title']) > 60:
								entry['data']['title'] = entry['data']['title'][:57] + '...'
							self.bot.sayAll(('r/{subreddit:s} : "{title:s}" by {author:s} ' + 
								'(http://www.reddit.com/r/{subreddit:s}/comments/{id:s})').format(**entry['data']))
				
					if len(entries):
						self.lastid = entries[0]['data']['id']
				except KeyError as e:
					pass
		except urllib.error.HTTPError as e:
			pass
		return True

