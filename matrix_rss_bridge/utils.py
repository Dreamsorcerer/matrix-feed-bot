import simplematrixbotlib as botlib
import toml


def validate_config(file_name):
  config = toml.load(file_name)
  try:
    config['homeserver']
    config['username']
    config['password']
    config['bridge']
    for bridge in config['bridge']:
      bridge['name']
      bridge['feed_url']
      bridge['room_id']
  except KeyError as e:
    raise ValueError(f"{e} not found in {file_name}")
  return config

def bot_factory(creds: botlib.Creds, func, args) -> botlib.Bot:
    bot = botlib.Bot(creds)

    @bot.listener.on_startup
    async def startup(room_id):
        await func(**args)