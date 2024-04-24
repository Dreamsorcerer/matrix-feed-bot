import asyncio
import hashlib
import json
import sys
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Required, TypedDict
from yarl import URL

import feedparser
import simplematrixbotlib as botlib
import yarl
from aiohttp import ClientSession
from liquid import Template
from nio import MatrixRoom, RoomMessage

FEEDS = Path("feeds")
FEEDS_DATA = FEEDS / "_data.json"


class FeedConfig(TypedDict, total=False):
    url: Required[str]
    template_md: str

FeedsData = dict[str, list[FeedConfig]]


@dataclass
class BotConfig(botlib.Config):
    homeserver: str = ""
    username: str = ""
    password: str | None = None
    access_token: str | None = None
    login_token: str | None = None
    interval: int = 3600


def feed_path(room_id: str, url: str) -> Path:
    h = hashlib.sha256(url.encode()).hexdigest()
    return FEEDS / f"{room_id}:{h}.xml"


class Bot:
    def __init__(self, creds: botlib.Creds, config: BotConfig):
        self._config = config
        self._bot = botlib.Bot(creds, config)
        self._bot.listener.on_message_event(self.on_message)
        try:
            self._feeds: FeedsData = json.loads(FEEDS_DATA.read_text())
        except OSError:
            self._feeds = {}

    async def on_message(self, room: MatrixRoom, message: RoomMessage) -> None:
        match message.body.split(maxsplit=3):
            case ("!rss", "subscribe", url, *template):
                feeds = self._feeds.setdefault(room.room_id, [])
                if any(f["url"] == url for f in feeds):
                    return

                feed = {"url": url}
                if template:
                    feed["template_md"] = template[0]

                async with ClientSession() as sess:
                    await self.update(sess, room.room_id, feed)
                feeds.append(feed)
                FEEDS_DATA.write_text(json.dumps(self._feeds))
            case ("!rss", "delete", url):
                feeds = self._feeds.pop(room.room_id, [])
                new_feeds = [f for f in feeds if f["url"] != url]
                if new_feeds:
                    self._feeds[room.room_id] = new_feeds
                FEEDS_DATA.write_text(json.dumps(self._feeds))
                feed_path(room.room_id, url).unlink(missing_ok=True)
            case ("!rss", "list"):
                feeds = self._feeds.get(room.room_id, ())
                msg = "\n".join(f"1. {f['url']}" for f in feeds) if feeds else "No feeds"
                await self._bot.api.send_markdown_message(room.room_id, msg)

    async def update(self, sess: ClientSession, room_id: str, feed: FeedConfig) -> None:
        path = feed_path(room_id, feed["url"])
        message_template = feed.get("template_md", "<h1>{{title}}</h1>\n\n{{published}}\n{{summary}}")
        template = Template(message_template)

        async with sess.get(URL(feed["url"], encoded=True)) as resp:
            rss = await resp.text()
            new = feedparser.parse(rss)

            if not path.is_file():
                entries = new.entries[:1]
            else:
                old = feedparser.parse(path.read_text())
                entries = [entry for entry in new.entries if entry not in old.entries]

            for entry in reversed(entries):
                msg = template.render(**entry)
                while msg:
                    if len(msg) > 30000:  # Can't send messages which are too long
                        i = msg.rfind("\n", 0, 30000)
                        part = msg[:i]
                        msg = msg[i+1:]
                    else:
                        part = msg
                        msg = ""
                    await self._bot.api.send_markdown_message(room_id, part)

            path.write_text(rss)

    async def loop(self) -> None:
        await asyncio.sleep(15)  # Small startup delay
        while True:
            async with ClientSession() as sess:
                t = (self.update(sess, r, f) for r, data in self._feeds.items() for f in data)
                await asyncio.gather(*t)
            await asyncio.sleep(self._config.interval)

    async def run(self) -> None:
        task = asyncio.create_task(self.loop())
        try:
            await self._bot.main()
        finally:
            task.cancel()
            await task


if __name__ == "__main__":
    FEEDS.mkdir(exist_ok=True)
    config = BotConfig()
    config.load_toml(sys.argv[1] if len(sys.argv) > 1 else "config.toml")
    if not config.homeserver or not config.username:
        raise ValueError("Missing config value for 'homeserver' or 'username'.")
    if not any((config.password, config.login_token, config.access_token)):
        raise ValueError("Config must contain 'password', 'login_token' or 'access_token'.")

    creds = botlib.Creds(
        homeserver=config.homeserver,
        username=config.username,
        password=config.password,
        login_token=config.login_token,
        access_token=config.access_token
    )

    bot = Bot(creds, config)
    asyncio.run(bot.run())
