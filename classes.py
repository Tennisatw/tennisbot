from configparser import ConfigParser

from telegram.ext import ContextTypes


class Function:

    def func(self, get_m, send_m, text):
        raise UserWarning

    Mandarin_prompt = ''
    English_prompt = ''
    Mandarin_help = ''
    English_help = ''
    developer_only = False


class Setting:

    @classmethod
    def get(cls, section):
        bot_config = 'bot_config.ini'
        config = ConfigParser()
        config.read(bot_config, encoding='utf-8')
        cls.bot_name = config[section]['bot_name']
        cls.chat_model = int(config[section]['chat_model'])
        cls.developer_mode = bool(config[section]['developer_mode'])
        cls.sending = bool(config[section]['sending'])

    @classmethod
    def save(cls, section):
        bot_config = 'bot_config.ini'
        config = ConfigParser()
        config.read(bot_config, encoding='utf-8')
        config.set(section, 'bot_name', cls.bot_name)
        config.set(section, 'chat_model', str(cls.chat_model))
        if cls.developer_mode:
            config.set(section, 'developer_mode', 'T')
        else:
            config.set(section, 'developer_mode', '')
        if cls.sending:
            config.set(section, 'sending', 'T')
        else:
            config.set(section, 'sending', '')
        config.write(open(bot_config, 'w', encoding='utf-8'))

    bot_name = '🥎'
    chat_model = 1
    developer_mode = False
    sending = True


class GetMessage:
    content = ''
    group = ''
    group_id = 0
    person = ''
    time = ''
    type = ''
    lang = 'zh-CN'


class SendMessage:
    """type=1: text message, type=2: image message, type=3: voice message, type=4: file message"""

    @classmethod
    async def send(cls, content=''):
        if content == '':
            content = cls.content

        if cls.type == 1:
            await cls.context.bot.send_message(chat_id=cls.group_id, text=content)
        elif cls.type == 2:
            await cls.context.bot.send_photo(chat_id=cls.group_id, photo=content)
        elif cls.type == 3:
            await cls.context.bot.send_voice(chat_id=cls.group_id, voice=content)
        elif cls.type == 0:
            pass
        print('\t'.join(['\033[33msend', '\033[0m', cls.group, content]))

    content = ''
    context = ContextTypes.DEFAULT_TYPE
    group = ''
    group_id = ''
    type = 1


sets = Setting
