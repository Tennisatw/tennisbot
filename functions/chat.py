from time import strftime
import openai

from classes import Function, GetMessage, SendMessage, sets


def chatgpt(question, lang='zh-CN'):
    def chat_core(file_addr, prom_add='', temp=1.0, freq_p=0.0, pres_p=0.0):
        file = open(file_addr, 'r', encoding='UTF-8')
        data = file.read().split('---\n')
        if len(data) > 1:
            prom = prom_add + data[0] + data[1] + 'Q: ' + question + '|\nA: '
        else:
            prom = prom_add + data[0] + 'Q: ' + question + '|\nA: '
        file.close()
        key = sets.chatGPT_token
        openai.api_key = key
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prom,
            max_tokens=400,
            top_p=1,
            temperature=temp,
            frequency_penalty=freq_p,
            presence_penalty=pres_p,
            stop=["|\n"]
        )
        ans = response['choices'][0]['text']
        return ans

    def get_date():
        return strftime("Now is %Y/%m/%d/ %H:%M %A|\n")

    answer = chat_core(f'files/chatgpt-{lang}/2-chat.txt', prom_add=get_date(), temp=1.0)

    file1 = open(f'files/chatgpt-{lang}/2-chat.txt', 'r', encoding='UTF-8')
    data_list = file1.read().split('---\n')
    if len(data_list) > 1:
        data1_new = data_list[1].split('|\n', 2)[2]
        data_list[1] = data1_new + 'Q: ' + question + '|\nA: ' + answer + '|\n'
        data_new = '---\n'.join(data_list)
        file3 = open(f'files/chatgpt-{lang}/2-chat.txt', 'w', encoding='UTF-8')
        file3.write(data_new)
    return answer


async def f_chat(get_m: GetMessage, send_m: SendMessage, text):
    await send_m.send(chatgpt(text[2], lang=get_m.lang))


chat = Function()
chat.func = f_chat
chat.Mandarin_prompt = '聊天'
chat.English_prompt = 'chat'
chat.Mandarin_help = f'''
与{sets.bot_name}聊天（使用chatGPT技术）
注：“聊天”一词可省略
在设置里面可以设置是否开启聊天模式
如开启，使用者发送的除了命令以外的信息，均会被当作在与{sets.bot_name}聊天
输入举例：
{sets.bot_name} 聊天 你好
{sets.bot_name} 今天天气怎么样？'''
chat.English_help = f'''
Chat with {sets.bot_name} (with the help of chatGPT)
note: the word "chat" can be omitted
One can enable or disable the "chat mode" in settings. 
If it is enabled, all the message sent by the user, except commands, will be regarded as chatting with {sets.bot_name}
Example：
-{sets.bot_name}-chat-hi there
-{sets.bot_name}-How is the weather like today?'''

# TODO 多种聊天模型
