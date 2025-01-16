import datetime
import json
import os
import re
import shutil

from util.config import MESSAGES, ROOT_PATH
from util.set import sets
from util.get_message import get_m


def record_chat_log(role, content, name):
    """
    在chat_log文件夹里记录用户的聊天记录
    Record user's chat history in chat_log folder
    """
        
    if not os.path.exists(f'{ROOT_PATH}/chat_log/{get_m.group}.json'):
        with open(f'{ROOT_PATH}/chat_log/{get_m.group}.json', 'w') as file_user:
            file_user.write('[]')
    with open(f'{ROOT_PATH}/chat_log/{get_m.group}.json', 'r', encoding='UTF-8') as file_user:
        record: list = json.load(file_user)

    name = re.sub("([^\u0030-\u0039\u0041-\u007a])", '', name)
    record.append({"role": role, "content": content, "name": name})
    
    # 如果聊天记录超过15条，则删除最早的一条，以节约TOKEN
    # If the chat history exceeds 15, delete the earliest one to save TOKEN
    if len(record) >= 15:
        record.pop(0)

    with open(f'{ROOT_PATH}/chat_log/{get_m.group}.json', 'w', encoding='UTF-8') as file_user:
        json.dump(record, file_user, ensure_ascii=False)
        
        
def history_clean():
    file = open(f'{ROOT_PATH}/chat_log/{get_m.group}.json', 'w', encoding='UTF-8')
    file.write('[]')
    file.close()
    return MESSAGES.get(sets.lang, {}).get("history_clean", '')


def history_save():
    time_now = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    source = f'{ROOT_PATH}/chat_log/{get_m.group}.json'
    target = f'{ROOT_PATH}/chat_log/save_chat/{get_m.group}-{time_now}.json'
    shutil.copy(source, target)
    return MESSAGES.get(sets.lang, {}).get("history_save", '')