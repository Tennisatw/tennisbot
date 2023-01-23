from re import search, IGNORECASE
from traceback import format_exc

from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes

from classes import GetMessage, SendMessage, sets
from functions.chat import chat
from functions.evaluate import evaluate
from functions.execute import execute
from functions.function_list import functionlist
from functions.help import help_b
from functions.keyboard import keyboard
from functions.mouse import mouse
from functions.raiseerror import raiseerror
from functions.screenshot import screenshot
from functions.setting import set_b
from functions.speak import speak

function_list = [chat, evaluate, execute, functionlist, help_b,
                 keyboard, mouse, raiseerror, screenshot, set_b,
                 speak]


async def treat(split=' '):
    global get_m
    global send_m
    text: list = get_m.content.split(split)
    for i in range(3):
        text.append('')
    for function in function_list:
        if function.Mandarin_prompt == text[1]:
            if (not sets.developer_mode) and function.developer_only:
                await send_m.send('没有权限使用此功能，请打开开发者模式')
                return
            print('\t'.join(['\033[35mtreat', '\033[0m'] + text))
            get_m.lang = 'zh-CN'
            if text[2] == '帮助':
                await send_m.send(function.Mandarin_help)
                return
            else:
                await function.func(get_m, send_m, text)
                return
        elif function.English_prompt == text[1]:
            if (not sets.developer_mode) and function.developer_only:
                await send_m.send('permission denied, please enable developer mode')
                return
            print('\t'.join(['\033[35mtreat', '\033[0m'] + text))
            get_m.lang = 'en-US'
            if text[2] == 'help':
                await send_m.send(function.English_help)
                return
            else:
                await function.func(get_m, send_m, text)
                return
    await chat.func(get_m, send_m, text)


async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global get_m
    global send_m
    try:
        get_m = GetMessage
        get_m.content = update.effective_message.text
        get_m.group = update.effective_chat.title
        get_m.group_id = update.effective_chat.id
        get_m.person = update.effective_message.author_signature
        if get_m.person is None:
            get_m.group = update.effective_chat.full_name
            get_m.person = update.effective_chat.full_name
        get_m.time = str(update.effective_message.date.today()).split('.')[0]

        send_m = SendMessage
        send_m.context = context
        send_m.group = get_m.group
        send_m.group_id = get_m.group_id
        send_m.type = 1

        if section != get_m.group:
            sets.get(get_m.group)

        print('\t'.join(['\033[32mget ', '\033[0m', get_m.group, get_m.person, get_m.time, get_m.content]))

        for bn in ['Tennisbot', 'tb', sets.bot_name]:
            s_result = search(f'^{bn} ', get_m.content, IGNORECASE)
            if s_result is not None:
                await treat()
                return
            s_result = search(f'^{bn},', get_m.content, IGNORECASE)
            if s_result is not None:
                await treat(',')
                return
            s_result = search(f'^(.){bn}', get_m.content, IGNORECASE)
            if s_result is not None:
                get_m.content = get_m.content.split(s_result.group(1), 1)[1]
                await treat(s_result.group(1))
                return
        if sets.chat_model != 0:
            await chat.func(get_m, send_m, [{sets.bot_name}, '普通聊天', get_m.content])

    except Exception as exc:
        if get_m.lang == 'zh-CN':
            str_er = f'{sets.bot_name}出现了一个错误：'
        elif get_m.lang == 'en-US':
            str_er = 'There is an error occurred: '
        else:
            str_er = ''
        await send_m.send(str_er + repr(exc))
        print(format_exc())


if __name__ == '__main__':
    section = 'DEFAULT'
    language = 'zh-CN'
    sets.get_token()
    application = ApplicationBuilder().token(sets.telegram_token).build()

    get_m = GetMessage
    send_m = SendMessage

    echo_handler = MessageHandler(filters.TEXT, get_message)
    application.add_handler(echo_handler)
    application.run_polling()
