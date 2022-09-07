import asyncio, os
import simplematrixbotlib as botlib
import feedparser
import aiohttp
from matrix_rss_bridge import validate_config, bot_factory


async def loop(bot, interval, bridges):
  async def check_feed(session, bridge):
    name, url, room_id = bridge['name'], bridge['feed_url'], bridge['room_id']

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
        message = f"<h1>{entry['title']}</h1>\n\n{entry['published']}\n{entry['link']}\n\n{entry['content'][0]['value']}"
        await bot.api.send_markdown_message(room_id, message)

  while True:
    await asyncio.sleep(0.01+interval)
    async with aiohttp.ClientSession() as session:
      for bridge in bridges:
        await check_feed(session, bridge)

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
