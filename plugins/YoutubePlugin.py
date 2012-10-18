"""
YoutubePlugin by itsmartin

config: none
"""

import re, urllib.request, json
import pyirc.Plugin

class YoutubePlugin(pyirc.Plugin.Plugin):

	def handleChat(self, chan, sender, msg):
		m = re.search("(?:youtube.com\\/watch\\?(?:.*&)?v=|youtu.be\\/)([\\w-]*)", msg, re.IGNORECASE)
		if m:
			videoDataUrl = "https://gdata.youtube.com/feeds/api/videos/%s?v=2&alt=json" % m.group(1)
			response = urllib.request.urlopen(videoDataUrl).readall().decode('utf-8')
			videoData = json.loads(response)

			author = videoData["entry"]["media$group"]["media$credit"][0]["yt$display"]
			title = videoData["entry"]["media$group"]["media$title"]["$t"]
			duration = self._formatSeconds(int(videoData["entry"]["media$group"]["yt$duration"]["seconds"]))
			
			self.bot.say(chan, '%s posted "%s" by %s [%s]' % (sender, title, author, duration))

		return True

	def _formatSeconds(self, seconds):
		hours = int(seconds / 3600)
		seconds = seconds % 3600

		minutes = int(seconds / 60)
		seconds = seconds % 60

		if hours > 0:
			return "%02d:%02d:%02d" % (hours, minutes, seconds)
		else:
			return "%02d:%02d" % (minutes, seconds)

