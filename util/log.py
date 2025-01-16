import logging
import os
import time


class Logs(object):

    def __init__(self, filename, level='info'):
        self.logger = logging.Logger(filename)
        self.logger.setLevel(self.level_relations.get(level))

        th_format_str = logging.Formatter(self.th_format)
        th = logging.FileHandler(filename=filename, encoding='utf-8')
        th.setFormatter(th_format_str)
        self.logger.addHandler(th)

        sh_format_str = logging.Formatter(self.sh_format)
        sh = logging.StreamHandler()
        sh.setFormatter(sh_format_str)
        self.logger.addHandler(sh)

    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL}

    # sh_format = "\033[7m%(levelname)s\033[0m\033[2m\t%(message)s"
    sh_format = "%(levelname)s\t%(message)s"
    th_format = "%(asctime)s %(levelname)s %(pathname)s %(funcName)s %(lineno)s\n%(message)s"


log_path = str(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logs= Logs(f"{log_path}/log/{time.strftime('%Y-%m-%d_%H-%M-%S')}.log")