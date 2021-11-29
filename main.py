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

    filter_week = [13, 14]
    bot = Bot(config, filter_week=filter_week, have_email=True, force_send_email=True)
    bot.run()
