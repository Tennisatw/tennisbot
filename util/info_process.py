import json
import os
import random
import re
import subprocess
import sys

import discord

from util.config import MESSAGES, ROOT_PATH
from util.set import sets
from util.log import logs
from util.get_message import get_m
from util.send_message import send_m
from util.mdcb import mdcb

from util.func_chat_log import *
from util.func_file import *
from util.functions import *

if os.path.exists(f'{ROOT_PATH}/files/gmail.json'):
    from util.func_email import email_get, email_send


async def info_process(param):
    """
    param = [info, n_tb, poker_face, recursion]
    
    处理mind_cube返回的信息
    info: 用户输入的信息
    n_tb: 当前的Tennisbot编号
    poker_face: 使用Tennisbot人格化回复，还是使用openai默认回复
    recursion: 是否是递归处理
    
    Processing the information returned by mind_cube
    info: the user's input
    n_tb: the current Tennisbot number
    poker_face: Reply with Tennisbot's personality or openai's default reply
    recursion: whether it is a recursive process
    """
    
    info = param[0]
    n_tb = param[1] if len(param) > 1 else 0
    poker_face = param[2] if len(param) > 2 else False
    recursion = param[3] if len(param) > 3 else False
    
    record_chat_log(role='user', content=info, name=get_m.person)

    if not info:
        return

    send_text = f'{sets.bot_name}{MESSAGES.get(sets.lang, {}).get("thinking", "")}'
    with open(f'{ROOT_PATH}/files/emojis.json', 'r') as file_emoji:
        emoji_list = json.load(file_emoji)
    emoji = random.choice(emoji_list)
    thinking_message = await send_m.send_thinking(send_text + emoji)
    
    client = send_m.client
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name=get_m.person))

    result_list = []

    # 如果info以'&'开头，则将info作为命令语句
    # 否则将info作为普通语句，使用mdcb处理，并处理mdcb的输出
    # 在提示词中，指示Tennisbot将命令用'⟨⟩'括起来
    # If info starts with '&', then info is treated as a command statement
    # Otherwise, info is treated as a normal statement, processed by mdcb, 
    # and the output of mdcb is processed
    # In the prompt, instruct Tennisbot to wrap the command with '⟨⟩'
    if info.startswith('&'):
        result_list.append('✪' + info[1:])
    else:
        raw_results = mdcb(info, n_tb=n_tb, poker_face=poker_face, recursion=recursion)
        if n_tb == 0:
            record_chat_log(role='assistant', content=raw_results, name='Tennisbot')
        else:
            record_chat_log(role='assistant', content=raw_results, name='Tennisbot_' + str(n_tb))
        logs.logger.info('\t'.join(['mdcb', raw_results]))
        results = raw_results.replace('⟨', '⟨✪')
        result_list = re.split('⟨|⟩', results)

    # '✪'开头的语句为命令语句，其中'&'作为命令中函数名称，函数参数1，函数参数2...的分隔符
    # 不以'✪'开头的语句直接输出
    # The statement starting with '✪' is a command statement, 
    # where '&' is used as the separator for the function name, param 1, param 2, etc.
    # The statement not starting with '✪' is directly output
    program_outputs = []
    r_list = [""]
    for result in result_list:
        if not result.strip():
            continue
        if result.startswith('✪'):
            r_list = result[1:].split('&')

            if r_list[0] == 'bot_exit':
                await bot_exit()

            elif r_list[0] == 'bot_reboot':
                await bot_reboot()

            elif r_list[0] == 'file_send':
                print(r_list)
                output = file_send(r_list[1:])
                if len(output.split('\n')) == 1:
                    await send_m.send_document(output)
                else:
                    file_list = output.split('\n')
                    await send_m.send_message(file_list[0])
                    for file in file_list[1:]:
                        await send_m.send_document(file)
            
            # “info_process” 功能本身支持递归（自动多开），这一点也提示Tennisbot了
            # Function "info_process" itself supports recursion, 
            # which is also indicated to Tennisbot
            elif r_list[0] == 'info_process':
                for output in program_outputs:
                    record_chat_log('user', output, 'program_output')
                await info_process([r_list[1], n_tb, poker_face, True])
                
            else:
                try:
                    # 执行任意定义在util/functions.py中的函数，在提示词中已详介函数名与参数
                    # 它也有执行到其他函数的风险，但我认为这属于Tennisbot的特色，故保留此风险
                    # Execute any function defined in util/functions.py, 
                    # The function name and parameters are detailed in the prompt
                    # It also has the risk of executing other functions, 
                    # but I think this is a feature of Tennisbot, so I keep this risk
                    if len(r_list) == 1:
                        output = globals()[r_list[0]]()
                    else:
                        output = globals()[r_list[0]](r_list[1:])
                    program_outputs.append(output)
                    await send_m.send_message('|' + output)
                except KeyError:
                    text = MESSAGES.get(sets.lang, {}).get("func_error", '').format(func_name=r_list[0])
                    logs.logger.warning(text)
                    program_outputs.append(text)
                    await send_m.send_message(text)
        else:
            await send_m.send_message(result)
    if r_list[0] != 'info_process':
        for output in program_outputs:
            record_chat_log('user', output, 'program_output')

    await send_m.send_delete(thinking_message.id)
    await client.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=str(random.choice([*globals().keys()]))))


async def bot_exit():
    text = MESSAGES.get(sets.lang, {}).get("exit", '')
    await send_m.send_message(sets.bot_name + text)
    exit(0)
    # _exit(0)


async def bot_reboot():
    text = MESSAGES.get(sets.lang, {}).get("reboot", '')
    await send_m.send_message(sets.bot_name + text)
    sets.schedule.stop()
    os.spawnv(os.P_WAIT, sys.executable, [sys.executable] + sys.argv)
    exit(0)


def evaluate(param):
    text = param[0]
    try:
        return str(eval(text))
    except Exception as eval_exc:
        text = MESSAGES.get(sets.lang, {}).get("evaluate_error", ' ')
        return text + repr(eval_exc)


def execute(param):
    text = param[0]
    
    class StdoutRedirect:

        def __init__(self):
            self.content = ''

        def write(self, text):
            self.content += text

        def flush(self):
            self.content = ''
            
    try:
        stdout = StdoutRedirect()
        sys.stdout = stdout
        exec(text, globals(), locals())
        sys.stdout = sys.__stdout__
        result = stdout.content
        stdout.flush()

        text = MESSAGES.get(sets.lang, {}).get("execute_success", ' ')
        return text + result

    except Exception as exec_exc:
        text = MESSAGES.get(sets.lang, {}).get("execute_failed", ' ')
        return text + repr(exec_exc)


def execute_shell_command(param):
    text = param[0]
    try:
        cmd = subprocess.Popen(text, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return cmd.communicate()[0].decode(encoding=sys.getfilesystemencoding())
    except Exception as cmd_exc:
        text = MESSAGES.get(sets.lang, {}).get("command_error", ' ')
        return text + repr(cmd_exc)