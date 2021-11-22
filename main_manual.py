from bot_lite import Bot

import sys
import json

if __name__ == "__main__":
    config_file = 'config.json'
    if len(sys.argv) == 2:
        config_file = sys.argv[1]
    with open(config_file, encoding='utf-8') as fp:
        config = json.load(fp)

    bot = Bot(config, send_email=True)
    bot.run_manual_strategy()
    