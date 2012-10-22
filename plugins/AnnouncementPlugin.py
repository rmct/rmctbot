"""
AnnouncementPlugin by authorblues

config:
	calendars = a comma-seperated list of calendars to monitor
	delay-minutes = number of minutes between updates
	announcement-minutes = comma-seperated list of minutes to announce prior to an event
"""

import sys, urllib2, json
import datetime
import operator

import chatlib

class AnnouncementPlugin(chatlib.Plugin):
	def __init__(self, bot):
		super(type(self), self).__init__(bot)
		self.setIdleTimer(60.0)

		self.updateFrequency = 20
		self.updateTicks = 0
		self.lastCheck = datetime.datetime.now(chatlib.utc)

		self.feeds = dict()
		self.gcals = self.getConfig('calendars').split(',')
		self.processCalendars(*self.gcals)

		self.announceMinutes = [int(x.strip()) for x in self.getConfig('announcement-minutes').split(',')]

	def processCalendars(self, *cals):
		for gcal in cals:
			self.feeds['http://www.google.com/calendar/feeds/' + gcal.strip() + '/public/full?alt=json&max-results=5' +
				'&orderby=starttime&singleevents=true&sortorder=ascending&futureevents=true&ctz=Etc/GMT'] = None

	def handleCommand(self, chan, sender, cmd, args):
		if cmd == 'upcoming':
			nextevents = set()
			now = datetime.datetime.now(chatlib.utc)
			for url,feed in self.feeds.items():
				try:
					feed = self.feeds[url] = json.loads(urllib2.urlopen(url).read())

					if 'entry' not in feed['feed']: continue
					for entry in feed['feed']['entry']:
						try:
							# how long until the event takes place
							when = datetime.datetime.strptime(entry['gd$when'][0]['startTime'], 
								'%Y-%m-%dT%H:%M:%S.000Z').replace(tzinfo=chatlib.utc)
							nextevents.add((entry['title']['$t'], when))
							break
						except ValueError as e:
							pass

				except urllib2.HTTPError as e:
					pass

			if not len(nextevents):
				self.bot.say(chan, 'No upcoming events are scheduled at this time.')
				return True

			title, when = min(nextevents, key=operator.itemgetter(1))
			howlong = (when - now).total_seconds() // 60
			self.bot.say(chan, 'Next event is "{:s}" starting {:s}'.format(title, m2time(howlong)))
			return True

	def idle(self):
		for url,feed in self.feeds.items():
			if self.updateTicks == 0:
				try:
					feed = self.feeds[url] = json.loads(urllib2.urlopen(url).read())
				except urllib2.HTTPError as e:
					pass

			now = datetime.datetime.now(chatlib.utc)
			if feed is not None and 'entry' in feed['feed']:
				for entry in feed['feed']['entry']:
					try:
						# how long until the event takes place
						when = datetime.datetime.strptime(entry['gd$when'][0]['startTime'], 
							'%Y-%m-%dT%H:%M:%S.000Z').replace(tzinfo=chatlib.utc)
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
