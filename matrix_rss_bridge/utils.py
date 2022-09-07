import simplematrixbotlib as botlib


def bot_factory(creds: botlib.Creds, func, args) -> botlib.Bot:
    bot = botlib.Bot(creds)

    @bot.listener.on_startup
    async def startup(room_id):
        await func(**args)