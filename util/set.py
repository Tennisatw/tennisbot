import configparser

from util.config import ROOT_PATH
from util.log import logs


class Sets:
    """
    获取和设置配置文件 (files/bot_config.ini) 中的参数。
    Get and set parameters in the configuration file (files/bot_config.ini).
    """
    _config_add = f'{ROOT_PATH}/files/bot_config.ini'
    _config = configparser.ConfigParser()
    
    def __init__(self):
        self.section = "default"
        self.schedule = None
        
        self.discord_token = ''
        self.discord_default_chat_id = ''
        self.chatGPT_token = ''
        
        self.bot_name = '🎾'
        self.chat_model = 'mini'
        self.chat_temperature = 0.5
        self.developer_mode = False
        self.lang = ''
        self.parallel = 1

    @classmethod
    def _get_config(cls, section):
        """
        从_config中读取参数
        Get parameters from the _config
        """
        cls.bot_name = cls._config[section]['bot_name']
        cls.chat_model = str(cls._config[section]['chat_model'])
        cls.chat_temperature = float(cls._config[section]['chat_temperature'])
        cls.developer_mode = bool(cls._config[section]['developer_mode'])
        cls.lang = cls._config[section]['language']
        cls.parallel = int(cls._config[section]['parallel'])
        
    @classmethod
    def _set_config(cls, section):
        """
        设置参数，并保存于_config中
        Set parameters and save them in the _config
        """
        if not cls._config.has_section(section):
            cls._config.add_section(section)
            
        cls._config.set(section, 'bot_name', cls.bot_name)
        cls._config.set(section, 'chat_model', cls.chat_model)
        cls._config.set(section, 'chat_temperature', str(cls.chat_temperature))
        cls._config.set(section, 'language', cls.lang)
        cls._config.set(section, 'parallel', str(cls.parallel))
        cls._config.set(section, 'developer_mode', 'T' if cls.developer_mode else '')
        
    @classmethod
    def get_token(cls):
        cls._config.read(cls._config_add, encoding='utf-8')
        section = 'TOKENS'
        try:
            cls.discord_token = cls._config[section]['discord']
            cls.discord_default_chat_id = cls._config[section]['discord_default_chat_id']
            cls.chatGPT_token = cls._config[section]['chatGPT'   ]
        except KeyError:
            logs.logger.error(f'无法从files/bot_config.ini中获取token，请检查 - '
                              f'Cannot get token from files/bot_config.ini, please check')

    @classmethod
    def get_config(cls, section):
        cls.section = section
        cls._config.read(cls._config_add, encoding='utf-8')
        if cls._config.has_section(section):
            cls._get_config(section)
        else:
            logs.logger.warning(f'files/bot_config.ini中没有{section}这个用户，从默认设置中新建section - '
                              f'The user {section} is not in files/bot_config.ini, create a new section from default setting.')
            logs.logger.warning(f'可以修改 files/bot_config.ini 以定制{section}的使用体验 - '
                              f'Modify files/bot_config.ini to customize the usage experience of {section}')
            cls._get_config('default')
            cls._set_config(section)
            with open(cls._config_add, 'w', encoding='utf-8') as f:
                cls._config.write(f)

    @classmethod
    def set_config(cls, section):
        cls._set_config(section)
        with open(cls._config_add, 'w', encoding='utf-8') as f:
            cls._config.write(f)

sets = Sets