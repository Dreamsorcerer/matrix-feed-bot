import asyncio
import datetime
import difflib
import hashlib
import html
import json
import sys
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from textwrap import indent
from time import mktime
from types import MappingProxyType
from typing import Required, TypedDict

import feedparser
import jinja2
import simplematrixbotlib as botlib
from aiohttp import ClientSession
from nio import MatrixRoom, RoomMessage
from yarl import URL

FEEDS = Path("feeds")
FEEDS_DATA = FEEDS / "_data.json"
HEADERS = MappingProxyType({"User-Agent": "Mozilla/5.0"})
DEFAULT_TEMPLATE = """
<h1>
    {%- if link %}<a href="{{link}}">{% endif %}{{title}}{% if link %}</a>{% endif %}
    <sup><time>{{published}}</time></sup>
</h1>

{% if content -%}
<details>
    <summary>{{summary}}</summary>
    {{content}}
</details>
{%- elif summary -%}
{{summary}}
{%- endif -%}
"""


class EntryDetails(TypedDict):
    """Parameters to go in template."""
    title: str
    link: str | None
    summary: str
    content: str
    published: str


class FeedConfig(TypedDict, total=False):
    url: Required[str]

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


def format_diff(line: str) -> str:
    line = html.escape(line, quote=False)
    if line.startswith("+ "):
        line = f"<span data-mx-bg-color='#dafbe1' data-mx-color='#1f2328'>{line}</span>"
    elif line.startswith("- "):
        line = f"<span data-mx-bg-color='#ffebe9' data-mx-color='#1f2328'>{line}</span>"
    elif line.startswith("? "):
        line = f"<span data-mx-bg-color='#afd9ff' data-mx-color='#1f2328'>{line.rstrip()}</span>"
    return line


class Bot:
    def __init__(self, creds: botlib.Creds, config: BotConfig):
        self._config = config
        self._template = jinja2.Template(DEFAULT_TEMPLATE, enable_async=True)
        self._diff = difflib.Differ()
        self._bot = botlib.Bot(creds, config)
        self._bot.listener.on_message_event(self.on_message)
        try:
            self._feeds: FeedsData = json.loads(FEEDS_DATA.read_text())
        except OSError:
            self._feeds = {}

    def details_from_entry(self, entry: feedparser.FeedParserDict) -> EntryDetails:
        date = str(datetime.datetime.fromtimestamp(mktime(entry.published_parsed)))
        summary = entry.get("summary", "").strip()
        content = "\n\n".join(c["value"] for c in getattr(entry, "content", ()) if "html" in c["type"].lower())
        if content.strip() == summary:
            summary = content.lstrip().split("\n", maxsplit=1)[0]
        return {"title": entry.get("title", "??"), "link": entry.get("link"),
                "summary": summary, "content": content, "published": date}

    async def on_message(self, room: MatrixRoom, message: RoomMessage) -> None:
        match message.body.split(maxsplit=3):
            case ("!rss", "subscribe", url):
                feeds = self._feeds.setdefault(room.room_id, [])
                if any(f["url"] == url for f in feeds):
                    return
                feed = {"url": url}

                async with ClientSession(headers=HEADERS) as sess:
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
        async with sess.get(URL(feed["url"], encoded=True)) as resp:
            rss = await resp.text()
            if not resp.ok:
                msg = "Error fetching {}:\n{}".format(feed["url"], indent(rss, "  "))
                await self._bot.api.send_text_message(room_id, msg, "m.notice")
                return
            new = feedparser.parse(rss)

            if not path.is_file():
                entries = new.entries[:1]
            else:
                old = feedparser.parse(path.read_text())
                entries = []
                for entry in new.entries:
                    for old_entry in old.entries:
                        if entry.published == old_entry.published and entry.title == old_entry.title:
                            if not hasattr(entry, "content"):
                                break
                            content = "\n\n".join(c["value"] for c in entry.content if "html" in c["type"].lower())
                            old_content = "\n\n".join(c["value"] for c in old_entry.content if "html" in c["type"].lower())
                            if content == old_content:
                                break
                            diff_g = self._diff.compare(old_content.split("\n"), content.split("\n"))
                            diff = "\n".join(format_diff(l) for l in diff_g if not l.startswith("  "))
                            entry.pop("content")
                            entry["summary"] = f"<pre>{diff}</pre>"
                            entry["title"] = "<em>Edit:</em> " + entry.title
                    else:
                        entries.append(entry)

            for entry in reversed(entries):
                msg = await self._template.render_async(**self.details_from_entry(entry))
                while msg:
                    if len(msg) > 30000:  # Can't send messages which are too long
                        i = msg.rfind("\n", 0, 30000)
                        part = msg[:i] + "</details>"
                        msg = "<details><summary>...continued</summary>" + msg[i+1:]
                    else:
                        part = msg
                        msg = ""
                    await self._bot.api.send_markdown_message(room_id, part)

            path.write_text(rss)

    async def loop(self) -> None:
        await asyncio.sleep(15)  # Small startup delay
        while True:
            async with ClientSession(headers=HEADERS) as sess:
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
