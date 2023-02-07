import simplematrixbotlib as botlib
import toml

def validate_auth(config):
    if not any(auth_method in config for auth_method in ['password', 'access_token']):
            config['password nor access_token']

def validate_config(file_name):
  config = toml.load(file_name)
  try:
    config['homeserver']
    config['username']
    config['interval']
    config['bridge']
    validate_auth(config)
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
        await func(bot, *args)
    
    return bot