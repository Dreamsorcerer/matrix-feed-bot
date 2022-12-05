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
interval = 60 # seconds

[[bridge]]
    name = "matrix.org blog"
    feed_url = "https://matrix.org/blog/feed"
    room_id = "!AUweUQXCxcVfFOaOIU:matrix.org"
```

### Running

```sh
python3 -m poetry run bridge
```

## Docker

- Build the docker image:

```
docker build . -t matrix-rss-bridge
```

- Create `config.toml` from [here](#config)
- Run bridge

```
docker run -v $(pwd)/config.toml:/app/config.toml:ro matrix-rss-bridge:latest
```

- **Optionally** it can be build and run with `docker-compose` with the [`docker-compose.yaml`](docker-compose.yaml) file.

    - build the image: `docker-compose build`
    - run the service: `docker-compose up -d`
    - check logs: `docker-compose logs -f`
    - stop the service: `docker-compose stop`
    - bring down the service: `docker-compose down`

## Misc

- Free and Open Source, Licensed under the GPL-3.0-only license.
