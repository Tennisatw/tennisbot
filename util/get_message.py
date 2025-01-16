import datetime
import requests


class GetMessage:
    """
    从Discord频道获取消息
    type=1: 文本, type=2: 图片, type=3: 语音, type=4: 文件
    Get message from discord channel
    type=1: text message, type=2: photo message, type=3: voice message, type=4: file message
    """

    def __init__(self):
        self.content = ''
        self.group = ''
        self.group_id = ''
        self.message_id = ''
        self.link = ''
        self.person = ''
        self.time = datetime.datetime.today()
        self.type = ''

    def download(self, url, file_name):
        response = requests.get(url)
        with open(file_name, 'wb') as file:
            file.write(response.content)
    
get_m = GetMessage()