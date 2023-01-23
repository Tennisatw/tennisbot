from classes import Function, GetMessage, SendMessage, sets


async def f_help(get_m: GetMessage, send_m: SendMessage, text):
    await send_m.send(f'''
你好，这里是{sets.bot_name}，一个可以聊天，帮助干活的机器人。
本机器人由网球玩的人（qq846274848）编写
本机器人会回应以其名字开始的语句，其具体格式为：
{sets.bot_name} 命令( 参数1)( 参数2)...
{sets.bot_name},命令(,参数1)(,参数2)...
各参数之间可以用空格分隔，也可用英文逗号分隔，这两者不能混用
如在{sets.bot_name}之前输入1个字符，则可用那个字符当作分隔符，其具体格式为：
~{sets.bot_name}~命令(~参数1)(~参数2)...
可以使用“{sets.bot_name}”，“tennisbot”和“tb”触发{sets.bot_name}。不区分大小写
输入举例：
tb 计算 1000-7
{sets.bot_name} 说话 我才不是机器人呢，我是个生活在虚拟世界的真~人。 语速=5
tennisbot,报错
~tennisbot~聊天~Hi there

使用命令“功能列表”可查看{sets.bot_name}全部功能
{sets.bot_name} 功能列表
使用命令“设置”可设置tennisbot的运行参数
{sets.bot_name} 设置 某一项设置
※特别提示：在使用任一功能时，均可在其后加上“帮助”来查看其具体说明与输入格式
{sets.bot_name} 命令 帮助''')


help_b = Function()
help_b.func = f_help
help_b.Mandarin_prompt = '帮助'
help_b.English_prompt = 'help'
help_b.Mandarin_help = '''
你即使在帮助里也是需要帮助的吗？'''
help_b.English_help = '''
Do you still need help when you are in the help section?'''
