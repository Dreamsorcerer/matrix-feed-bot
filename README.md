# matrix-rss-bridge

A bridge for reading RSS feeds in Matrix rooms.

## Setup

Requires Python ^3.8

```sh
python3 -m pip install poetry
git clone https://gitlab.com/imbev/matrix-rss-bridge.git
cd matrix-rss-bridge
python3 -m poetry install
```

## Usage

### Config

Create `config.toml` to configure the bridge.

```toml
# config.toml
homeserver = "https://example.com"
username = "username" 
password = "password"

[[bridge]]
    name = "matrix.org blog"
    feed_url = "https://matrix.org/blog/feed"
    room_id = "!AUweUQXCxcVfFOaOIU:matrix.org"
```

### Running

```sh
python3 -m poetry run bridge
```

## Misc

- Free and Open Source, Licensed under the GPL-3.0-only license.
