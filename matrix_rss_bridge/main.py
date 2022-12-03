import asyncio, os
import simplematrixbotlib as botlib
import feedparser
from liquid import Template
import aiohttp
from matrix_rss_bridge import validate_config, bot_factory


async def loop(bot, interval, bridges):
  async def check_feed(session, bridge):
    name, url, room_id = bridge['name'], bridge['feed_url'], bridge['room_id']
    message_template = dict.get(bridge, 'template_markdown', '<h1>{{title}}</h1>\n\n{{published}}\n{{summary}}')
    template = Template(message_template)

    async with session.get(url) as resp:
      rss = await resp.text()
      new_parsed = feedparser.parse(rss)

      if not os.path.isfile(f'.feeds/{name}.xml'):
        entries = new_parsed.entries
      else:

        with open(f'.feeds/{name}.xml') as f:
          old_parsed = feedparser.parse(f.read())
          entries = []
          for entry in new_parsed.entries:
            if not entry in old_parsed.entries:
              entries.append(entry)

      with open(f'.feeds/{name}.xml', 'w') as f:
        f.write(str(rss))

      for entry in entries:
        message = template.render(**entry)
        await bot.api.send_markdown_message(room_id, message)

  while True:
    await asyncio.sleep(0.01+interval)
    async with aiohttp.ClientSession() as session:
      await asyncio.gather(*tuple([check_feed(session, bridge) for bridge in bridges]))

def main():
  if not os.path.isdir('.feeds'):
    os.mkdir('.feeds')
  config = validate_config("config.toml")
  creds = botlib.Creds(
    config['homeserver'],
    config['username'],
    config['password']
  )
  bot = bot_factory(
    creds, loop, [
      config['interval'], config['bridge']
      ]
    )
  bot.run()

if __name__ == '__main__':
    main()
