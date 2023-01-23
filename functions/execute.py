from classes import Function, GetMessage, SendMessage, sets


async def f_execute(get_m: GetMessage, send_m: SendMessage, text):
    exec_cmd = text[2]
    try:
        exec(exec_cmd)
    except Exception as exec_exc:
        await send_m.send('执行失败\n' + repr(exec_exc))


execute = Function()
execute.func = f_execute
execute.developer_only = True
execute.Mandarin_prompt = '执行'
execute.English_prompt = 'execute'
execute.Mandarin_help = f'''
执行一段python代码
输入举例：
{sets.bot_name} 执行 print("HelloWorld")
？{sets.bot_name}？执行？''' + '''from os import getcwd
from time import strftime
print(getcwd())
file = open(getcwd() + '/test.py', 'a', encoding='utf-8')
file.write(f'\\n# {strftime("%Y/%m/%d %H:%M")} tennisbot到此一游')
file.close()'''
execute.English_help = ''  # TODO
