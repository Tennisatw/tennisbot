import json
import re
import time

import requests

from util.config import MESSAGES, ROOT_PATH
from util.set import sets
from util.log import logs
from util.get_message import get_m


def mdcb(question: str, n_tb=0, cont=None, poker_face=False, recursion=False):
    """
    心智魔方, Tennisbot与gpt api在此交互
    cont: 如果上一轮对话超过长度限制，则将上一轮对话的回答, 作为cont传入
    poker_face: 是否开启扑克脸(即不使用Tennisbot提示词)
    recursion: 是否是(在info_process层面上的)自动递归调用
    Mind_Cube, Allow Tennisbot to communicate with gpt api
    cont: If the previous conversation exceeds the length limit, the previous conversation's answer will be passed in as cont
    poker_face: Whether to enable poker face (i.e., not using Tennisbot prompt)
    recursion: Whether it is (in the info_process layer) an automatic recursive call
    """
    headers = {"Authorization": f"Bearer {sets.chatGPT_token}", "Content-Type": "application/json"}
    if poker_face:
        max_tokens = 1000
        conversation = [{"role": "user", "content": question}]
    else:
        max_tokens = 200
        with open(f'{ROOT_PATH}/mdcb/{sets.lang}-system.txt', 'r', encoding='UTF-8') as file_system:
            conv_system = file_system.read()
            conv_system = conv_system.replace("ROOT_PATH", ROOT_PATH)
        with open(f'{ROOT_PATH}/mdcb/{sets.lang}-functions.txt', 'r', encoding='UTF-8') as file_func:
            conv_func = file_func.read()
        with open(f'{ROOT_PATH}/mdcb/{sets.lang}-conv.json', 'r', encoding='UTF-8') as file_conv:
            conv_conv = json.load(file_conv)
        try:
            with open(f'{ROOT_PATH}/chat_log/{get_m.group}.json', 'r', encoding='UTF-8') as file_user:
                conv_user = json.load(file_user)
        except FileNotFoundError:
            with open(f'{ROOT_PATH}/chat_log/{get_m.group}.json', 'w', encoding='UTF-8') as file_user:
                file_user.write('[]')
                conv_user = []
                
        if n_tb > 0:
            parallel_word = MESSAGES.get(sets.lang, {}).get("parallel_word", '').format(parallel=sets.parallel, n_tb=n_tb)
        else:
            parallel_word = ''

        conversation = [{"role": "system", "content": conv_system + conv_func} ]
        time_info = MESSAGES.get(sets.lang, {}).get("time_word", '') + time.strftime("%Y-%m-%d %H:%M %A")
        conv_info = [{"role": "system", "content": time_info + parallel_word}]
        conversation.extend(conv_info)
        conversation.extend(conv_conv)
        conversation.extend(conv_user)

        name = re.sub("([^\u0030-\u0039\u0041-\u007a])", '', get_m.person)
        if recursion:
            conversation.append({"role": "user", "content": question, "name": "Tennisbot"})

        if cont:
            continue_word = MESSAGES.get(sets.lang, {}).get("continue_word", '')
            conversation.append({"role": "assistant", "content": cont, "name": "Tennisbot"})
            conversation.append({"role": "user", "content": continue_word, "name": name})

    if sets.chat_model == 'full':
        model = "gpt-4o"
    elif sets.chat_model == 'mini':
        model = "gpt-4o-mini"
    else:
        return MESSAGES.get(sets.lang, {}).get("no_chat_model", '')
    temp = float(sets.chat_temperature)

    logit_bias = {20551: +2, 20308: +2, 21909: +2, 6447: +2,
                  13821: -5, 106: -3, 24326: -5, 109: -3, 15722: -5, 231: -3}
    # 耶+2 啦+2 ~+2 ！+2
    # 帮-5 抱歉-5

    data = {
        "messages": conversation,
        "max_tokens": max_tokens,
        "temperature": temp,
        "model": model,
        "logit_bias": logit_bias
    }
    
    # with open(f'{ROOT_PATH}/mdcb/latest_data.json', "w", encoding='UTF-8') as msg_file:
    #     json.dump(data, msg_file, ensure_ascii=False)
    
    mdcb_response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        data=json.dumps(data)
    )
    continuing = False
    if mdcb_response.status_code == 200:
        result = mdcb_response.json()
        generated_text = result["choices"][0]["message"]['content']
        answer = generated_text.strip()
        if result["choices"][0]["finish_reason"] == 'length':
            continuing = True
    else:
        answer = MESSAGES.get(sets.lang, {}).get("mdcb_no_return", '')
        logs.logger.warning(answer + " " + mdcb_response.text)

    if cont:
        answer = cont + answer

    if continuing:
        if len(answer) > 1000:
            text = MESSAGES.get(sets.lang, {}).get("mdcb_max_tokens", '')
            answer = answer + '\n' + text
            logs.logger.warning(text)
        else:
            answer = mdcb(question, n_tb=n_tb, cont=answer, poker_face=poker_face, recursion=recursion)
    return answer.replace('&lt;', '⟨').replace('&gt;', '⟩').replace('&amp;', '&')

