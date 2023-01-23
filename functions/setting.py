from classes import Function, GetMessage, SendMessage, sets


async def f_setting(get_m: GetMessage, send_m: SendMessage, text):
    if text[2] == '名字':
        if text[3] == '帮助':
            await send_m.send(f'更改{sets.bot_name}的名字\n'
                              f'注：无论名字是什么，{sets.bot_name}也会把“Tennisbot”和“tb”当作自己的名字\n'
                              f'另注：也许你想把{sets.bot_name}的名字改成“帮助”，但这是不合法的')
        elif text[3] != '':
            bot_name_old = sets.bot_name
            sets.bot_name = text[3]
            sets.save(get_m.group)
            await send_m.send(f'{bot_name_old}已被重命名为{sets.bot_name}')
        else:
            await send_m.send(f'名字不能为空')

    elif text[2] == '聊天模式':
        if text[3] == '帮助':
            await send_m.send(f'设置{sets.bot_name}是否将不含有{sets.bot_name}的信息识别成与其聊天\n'
                              f'如处在聊天模式，则{sets.bot_name}会回应每一条消息（可能会比较烦人（以及比较费钱））\n'
                              f'使用0和1来控制，当前为{sets.chat_model}')
        elif text[3] == '1':
            sets.chat_model = 1
            sets.save(get_m.group)
            await send_m.send(f'{sets.bot_name}进入聊天模式')
        elif text[3] == '0':
            sets.chat_model = 0
            sets.save(get_m.group)
            await send_m.send(f'{sets.bot_name}退出聊天模式')
    # TODO 多种聊天模型
    elif text[2] == '开发者模式':
        if text[3] == '帮助':
            await send_m.send(f'设置是否可以使用{sets.bot_name}的一些进阶功能。\n'
                              f'这些功能可能会控制开发者的电脑，请谨慎使用\n'
                              f'使用T和F来控制，当前为{sets.developer_mode}')
        elif text[3] == 'T':
            sets.developer_mode = True
            sets.save(get_m.group)
            await send_m.send(f'{sets.bot_name}进入开发者模式')
        elif text[3] == 'F':
            sets.developer_mode = False
            sets.save(get_m.group)
            await send_m.send(f'{sets.bot_name}退出开发者模式')


set_b = Function()
set_b.func = f_setting
set_b.Mandarin_prompt = '设置'
set_b.English_prompt = 'set'
set_b.Mandarin_help = f'''
设置{sets.bot_name}的一些参数
可供设置的参数有：
名字，当前为{sets.bot_name}
聊天模式，当前为{sets.chat_model}
开发者模式，当前为{sets.developer_mode}
输入举例：
{sets.bot_name} 设置 名字 stupidbot
{sets.bot_name} 设置 聊天模式 T
在各项设置里也可使用帮助'''
set_b.English_help = ''''''  # TODO
