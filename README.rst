===============
matrix-feed-bot
===============

A bot for reading RSS/Atom feeds in Matrix rooms.

Setup
=====

Requires Python 3.11+.

Install the dependencies:
``pip install aiohttp feedparser Jinja2 simplematrixbotlib``

Then copy the ``matrix_feed_bot.py`` file to your server.

Config
======

Create a user account on the server to represent your bot.

Then create ``config.toml`` to configure the authentication details.

.. code-block:: toml

  [simplematrixbotlib.config]
  homeserver = "https://example.com"
  username = "username"
  password = "password"

If you don't want to use a password, you can use the account's access token.

.. code-block:: toml

  [simplematrixbotlib.config]
  homeserver = "https://example.com"
  username = "username"
  access_token = "some_long_string_that_represents_my_access_token"


You can also set ``interval`` to a custom number of seconds if you want to change the
frequency the bot will check for updates (defaults to 1 hour).

Further (generic) config options for the bot are available as documented at:
https://simple-matrix-bot-lib.readthedocs.io/en/latest/manual.html#built-in-values

Running
=======

Running is as simple as running the Python script:
``python matrix_feed_bot.py``

The script accepts an optional argument to allow a custom path to the config file:
``python matrix_feed_bot.py /path/to/config.toml``

The feed data will be saved in the ``feeds/`` directory under the current working directory.

Systemd
+++++++

To run this as a systemd service, you could create a simple service file like:

.. code-block::

  [Unit]
  Description=Matrix Feed Bot

  Wants=network.target
  After=syslog.target network-online.target

  [Service]
  Type=simple
  ExecStart=/usr/bin/python3 -O /path/to/matrix_feed_bot.py /path/to/config.toml
  KillMode=process
  PermissionsStartOnly=true
  Restart=always
  RestartSec=10
  TimeoutStopSec=60
  #User=user_to_run_as
  WorkingDirectory=/feed/data/will/be/stored/under/here/

  [Install]
  WantedBy=multi-user.target

Usage
=====

To use the bot, first invite the bot user to a room.

To subscribe to a feed in a room:
``!rss subscribe https://matrix.org/blog/feed``

The latest entry from the feed should then be posted into the room.

To view all feed subscriptions in a room:
``!rss list``

To unsubscribe from a feed:
``!rss delete https://matrix.org/blog/feed``
