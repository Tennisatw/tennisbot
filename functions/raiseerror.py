from classes import Function, GetMessage, SendMessage, sets


def f_raiseerror(get_m: GetMessage, send_m: SendMessage, text):
    if text[2] != '':
        custom_error = Exception
        raise custom_error(text[2])
    else:
        raise Exception


raiseerror = Function()
raiseerror.func = f_raiseerror
raiseerror.Mandarin_prompt = '报错'
raiseerror.English_prompt = 'raiseerror'
raiseerror.Mandarin_help = f'''
使{sets.bot_name}报一个错
如附加一个参数，则会报那个参数所指定的错
输入举例：
tennisbot 报错 
tennisbot 报错 没吃早饭'''
raiseerror.English_help = f'''
Let {sets.bot_name} raises an error
If another parameter is attached after, then this error's name is that parameter
Example：
tennisbot raiseerror 
tennisbot raiseerror too-hungry-to-work-error'''
