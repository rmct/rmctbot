import sys, urllib.request, json
import datetime

import pyirc.Plugin

class AnnouncementPlugin(pyirc.Plugin.Plugin):
	gcals = ['reddit.mctourney@gmail.com', 'admin@championsofthemap.com']
	feeds = dict()

	# number of minutes before the event to announce
	announceMinutes = [0, 60]

	def __init__(self, bot):
		super().__init__(bot)
		self.setIdleTimer(60.0)

		self.updateFrequency = 20
		self.updateTicks = 0
		self.lastCheck = datetime.datetime.now(datetime.timezone.utc)

	def idle(self):
		for url,feed in self.feeds.items():
			if self.updateTicks == 0:
				feed = self.feeds[url] = json.loads(urllib.request.urlopen(url).read().decode('utf8'))

			now = datetime.datetime.now(datetime.timezone.utc)
			if feed is not None and 'entry' in feed['feed']:
				for entry in feed['feed']['entry']:
					try:
						# how long until the event takes place
						when = datetime.datetime.strptime(entry['gd$when'][0]['startTime'], 
							'%Y-%m-%dT%H:%M:%S.000Z').replace(tzinfo=datetime.timezone.utc)
						howlong = when - now

						for minutes in self.announceMinutes:
							delta = datetime.timedelta(minutes=minutes)
							if howlong <= delta and when - self.lastCheck > delta:
								msg = '"{title:s}" starts {when:s}'.format(title=entry['title']['$t'], when=m2time(minutes))
								where = entry['gd$where'][0]['valueString']
								if len(where): msg += ' at {where:s}'.format(where=where)
								self.bot.sayAll('### ' + msg)
					except ValueError as e:
						pass

		self.updateTicks += 1
		self.updateTicks %= self.updateFrequency
		self.lastCheck = now
		return True

for gcal in AnnouncementPlugin.gcals:
	AnnouncementPlugin.feeds['http://www.google.com/calendar/feeds/' + gcal + '/public/full?alt=json' +
	    '&orderby=starttime&max-results=5&singleevents=true&sortorder=ascending&futureevents=true&ctz=Etc/GMT'] = None

def m2time(mn):
	if not mn: return 'now'

	s, k = [], mn
	units = [('m', 60), ('h', 24), ('d', 2**20)]
	for unit,cnt in units:
		n = k % cnt
		k = k // cnt
		if n:
			s.append('%d%s' % (n, unit))
		if not k: break
	return 'in ' + ' '.join(reversed(s))

