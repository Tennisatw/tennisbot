import configparser
import ctypes
import json
import os
import threading
import time

import _ssl
import httplib2
import requests

from util.config import ROOT_PATH
from util.log import logs

if os.path.exists(f'{ROOT_PATH}/files/gmail.json'):
    from util.func_email import email_get
else:
    email_get = lambda: 'None'


class Schedule(threading.Thread):
    """
    调度类，用于处理闹钟和定时器的功能。
    Schedule class for handling alarm and timer functions.
    """
    def get_config(self):
        schedule_config = f'{ROOT_PATH}/files/schedule.ini'
        config = configparser.ConfigParser()
        config.read(schedule_config, encoding='utf-8')
        self.alarm: dict = json.loads(config['default']['alarm'])
        self.timer: dict = json.loads(config['default']['timer'])

        bot_config = f'{ROOT_PATH}/files/bot_config.ini'
        config.read(bot_config, encoding='utf-8')
        self.lang = config['default']['language']

    def set_config(self):
        schedule_config = f'{ROOT_PATH}/files/schedule.ini'
        config = configparser.ConfigParser()
        config.read(schedule_config, encoding='utf-8')
        config.set('default', 'alarm', json.dumps(self.alarm))
        config.set('default', 'timer', json.dumps(self.timer))
        config.write(open(schedule_config, 'w', encoding='utf-8'))

    def run(self):
        logs.logger.info('thread已启动 - thread has started')
        while True:
            try:
                time.sleep(self.sleep_time)
                self.sleep_time = 30
                t_day = time.strftime("%w")
                if t_day == '0':
                    t_day = '7'
                t_time = time.strftime("%H:%M")

                for s_data in self.alarm.keys():
                    if '-' in s_data:
                        s_day, s_time = s_data.split('-', 1)
                        if (s_day == t_day) and (s_time == t_time):
                            self.sleep_time = 60
                            if self.lang == 'zh-CN':
                                send_sync(f'闹钟响铃 - {self.alarm[s_data]}')
                            elif self.lang == 'en-US':
                                send_sync(f'The alarm is ringing - {self.alarm[s_data]}')
                    else:
                        if s_data == t_time:
                            self.sleep_time = 60
                            if self.lang == 'zh-CN':
                                send_sync(f'闹钟响铃 - {self.alarm[s_data]}')
                            elif self.lang == 'en-US':
                                send_sync(f'The alarm is ringing - {self.alarm[s_data]}')

                for s_data in self.timer.keys():
                    if '-' in s_data:
                        s_day, s_time = s_data.split('-', 1)
                        if (s_day == t_day) and (s_time == t_time):
                            self.sleep_time = 60
                            self.timer.pop(s_data)
                            self.set_config()
                            if self.lang == 'zh-CN':
                                send_sync(f'定时器响铃 - {self.timer[s_data]}')
                            elif self.lang == 'en-US':
                                send_sync(f'The timer is ringing - {self.timer[s_data]}')
                    else:
                        if s_data == t_time:
                            self.sleep_time = 60
                            if self.lang == 'zh-CN':
                                send_sync(f'定时器响铃 - {self.timer[s_data]}')
                            elif self.lang == 'en-US':
                                send_sync(f'The timer is ringing - {self.timer[s_data]}')
                            self.timer.pop(s_data)
                            self.set_config()

                try:
                    email_result = email_get()
                    if email_result != 'None':
                        self.sleep_time = 1
                        if self.lang == 'zh-CN':
                            send_sync(f'收到新邮件\n{email_result}')
                        elif self.lang == 'en-US':
                            send_sync(f'Received a new email\n{email_result}')
                        mdcb_record_email(email_result)
                except (httplib2.ServerNotFoundError, _ssl.SSLEOFError, TimeoutError):
                    logs.logger.warning('收取email时无网络连接 - No network connection when retrieving email')
                except Exception as exc:
                    logs.logger.error(
                        f'收取email时出现了一个错误 - An error occurred when retrieving email: {repr(exc)}')
            except Exception as exc:
                logs.logger.error(f'thread出现了一个错误 - An error occurred in the thread: {repr(exc)}')
                if self.lang == 'zh-CN':
                    send_sync(f'thread出现了一个错误: {repr(exc)}')
                elif self.lang == 'en-US':
                    send_sync(f'An error occurred in the thread: {repr(exc)}')

    def stop(self):
        thread_id = 0
        # noinspection PyProtectedMember
        for t_id, thread in threading._active.items():
            if thread is self:
                thread_id = t_id
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
        logs.logger.info('\t'.join(['thread', 'thread已停止 - thread has stopped']))

    def pause(self, sleep_time=60):
        self.sleep_time = sleep_time

    alarm = {}
    timer = {}
    lang = ''
    sleep_time = 60


def send_sync(content, chat_id=0):
    bot_config = f'{ROOT_PATH}/files/bot_config.ini'
    config = configparser.ConfigParser()
    config.read(bot_config, encoding='utf-8')
    discord_token = 'Bot ' + config['TOKENS']['discord']
    if chat_id == 0:
        chat_id = config['TOKENS']['discord_default_chat_id']
    url = f'https://discord.com/api/v10/channels/{chat_id}/messages'
    auth = {'authorization': discord_token}
    msg = {'content': content}
    requests.post(url=url, headers=auth, data=msg)
    logs.logger.info('\t'.join(['send', 'sy-t', content]))


def mdcb_record_email(content, user='lkvijt-main'):
    with open(f'{ROOT_PATH}/files/mind_cube/chat_log/{user}.json', 'r', encoding='UTF-8') as file_user:
        conv_user: list = json.load(file_user)
    conv_user.append({"role": "user", "content": content, "name": "email"})
    if len(conv_user) > 15:
        while True:
            conv_user.pop(0)
            if conv_user[0]['name'] not in ['Tennisbot', 'program_output', 'email']:
                break
    with open(f'{ROOT_PATH}/files/mind_cube/chat_log/{user}.json', 'w', encoding='UTF-8') as file_user:
        json.dump(conv_user, file_user, ensure_ascii=False)
