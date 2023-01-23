import sys

from classes import Function, GetMessage, SendMessage, sets


class StdoutRedirect:
    content = ''

    def write(self, text):
        self.content += text

    def flush(self):
        self.content = ''


async def f_functionlist(get_m: GetMessage, send_m: SendMessage, text):
    if get_m.lang == 'zh-CN':
        code = f'''
from main import function_list
content = '{sets.bot_name}具有以下功能：'
for funct in function_list:
    if not funct.developer_only:
        content = content + ' ' + funct.Mandarin_prompt
print(content)'''
    else:
        code = f'''
from main import function_list
content = '{sets.bot_name} has the following functions:'
for funct in function_list:
    if not funct.developer_only:
        content = content + ' ' + funct.English_prompt
print(content)'''

    r = StdoutRedirect()
    sys.stdout = r
    exec(code, {'send_m': send_m})
    sys.stdout = sys.__stdout__
    await send_m.send(r.content)
    r.flush()


functionlist = Function()
functionlist.func = f_functionlist
functionlist.Mandarin_prompt = '功能列表'
functionlist.English_prompt = 'functionlist'
functionlist.Mandarin_help = f'''
查看{sets.bot_name}的功能列表'''
functionlist.English_help = f'''
list the functions of {sets.bot_name}'''
