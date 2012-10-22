import chatlib
channels = ['room@example.com']

bot = chatlib.Bot('username@example.com', passwd="password", debug=True)
bot.loadConfig('example.ini').loadPlugins('./plugins/').join(*channels).listen()
