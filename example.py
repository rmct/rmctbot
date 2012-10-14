from pyirc.Bot import Bot

bot = Bot('pyircbot', 'irc.freenode.net', debug=True)
bot.loadPlugins('./plugins/').join('#testroom').listen()
