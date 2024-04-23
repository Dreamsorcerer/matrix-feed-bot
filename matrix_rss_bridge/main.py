import asyncio, os, sys
from pathlib import Path
import simplematrixbotlib as botlib
import feedparser
from liquid import Template
import aiohttp
import yarl
from matrix_rss_bridge import validate_config, bot_factory

FEEDS = PATH(".feeds")


async def loop(bot, interval, bridges):
  async def check_feed(session, bridge):
    url = yarl.URL(bridge["feed_url"])
    room_id = bridge["room_id"]
    path = FEEDS / (url.host + url.path).rstrip("/").replace(".", "-").replace("/", "_") + ".xml"
    message_template = dict.get(bridge, 'template_markdown', '<h1>{{title}}</h1>\n\n{{published}}\n{{summary}}')
    template = Template(message_template)

    async with session.get(url) as resp:
      rss = await resp.text()
      new_parsed = feedparser.parse(rss)

      if not path.is_file():
        entries = new_parsed.entries
      else:
        old_parsed = feedparser.parse(path.read_text())
        entries = []
        for entry in new_parsed.entries:
          if not entry in old_parsed.entries:
            entries.append(entry)

      path.write_text(str(rss))

      for entry in reversed(entries):
        message = template.render(**entry)
        await bot.api.send_markdown_message(room_id, message)

  while True:
    async with aiohttp.ClientSession() as session:
      await asyncio.gather(*tuple([check_feed(session, bridge) for bridge in bridges]))
    await asyncio.sleep(0.01+interval)

def main():
  FEEDS.mkdir(exist_ok=True)
  config = validate_config(sys.argv[1] if len(sys.argv) > 1 else "config.toml")
  creds = botlib.Creds(
    config['homeserver'],
    config['username'],
    config['password'] if 'password' in config else None,
    config['login_token'] if 'login_token' in config else None,
    config['access_token'] if 'access_token' in config else None
  )
  bot = bot_factory(
    creds, loop, [
      config['interval'], config['bridge']
      ]
    )
  bot.run()

if __name__ == '__main__':
    main()
