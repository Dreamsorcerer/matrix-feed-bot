import toml


def validate_config(file_name):
  config = toml.load(file_name)
  try:
    config['homeserver']
    config['username']
    config['password']
    config['bridge']
    for bridge in config['bridge']:
      bridge['name']
      bridge['feed_url']
      bridge['room_id']
  except KeyError as e:
    raise ValueError(f"{e} not found in {file_name}")
  return config


def main():
  config = validate_config("config.toml")
  print(config)

if __name__ == '__main__':
    main()
