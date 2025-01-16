import os

import discord

from util.config import MESSAGES, ROOT_PATH
from util.set import sets
from util.on_message import MyClient
from util.schedules import Schedule
from util.send_message import send_sync

if __name__ == '__main__':

    # 初始化sets - init sets
    sets.get_config("default")
    sets.get_token()

    # 发送启动消息 - send start message
    start_message = MESSAGES.get(sets.lang, {}).get("start", f'{sets.bot_name}')
    send_sync(f'{sets.bot_name}{start_message}')

    # 初始化schedule - init schedule
    sets.schedule = Schedule(daemon=True)
    sets.schedule.get_config()
    sets.schedule.start()

    # 在第一次启动时发送欢迎消息 - send welcome message when first start
    log_path = os.path.join(ROOT_PATH, "log")
    number_of_logs = len([f for f in os.listdir(log_path)])
    if number_of_logs == 1:
        welcome_path = os.path.join(ROOT_PATH, "files/welcome.txt")
        with open(welcome_path, 'r', encoding='utf-8') as welcome:
            for welcome_line in welcome.readlines():
                send_sync(welcome_line)

    # 初始化客户端 - init client
    intents = discord.Intents.default()
    intents.message_content = True
    client = MyClient(intents=intents)
    client.run(sets.discord_token, log_handler=None)
