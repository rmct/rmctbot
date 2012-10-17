from pyirc.Bot import Bot

bot = Bot('pyircbot', 'irc.freenode.net', debug=True)
bot.loadConfig('example.ini').loadPlugins('./plugins/').join('#testroom').listen()
