from matrix_rss_bridge import validate_config, bot_factory


def main():
  config = validate_config("config.toml")
  print(config)

if __name__ == '__main__':
    main()
