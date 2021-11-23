from bot_lite import Bot

import sys
import os
import json

if __name__ == "__main__":
    config_file = os.path.join(sys.path[0], 'config.json')
    if len(sys.argv) == 2:
        config_file = sys.argv[1]
    with open(config_file, encoding='utf-8') as fp:
        config = json.load(fp)

    bot = Bot(config, have_email=False)
    bot.run_manual_strategy()
    