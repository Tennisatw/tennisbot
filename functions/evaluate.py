from classes import Function, GetMessage, SendMessage, sets


async def f_evaluation(get_m: GetMessage, send_m: SendMessage, text):
    eval_cmd = text[2]
    try:
        await send_m.send(str(eval(eval_cmd)))
    except Exception as eval_exc:
        await send_m.send('计算失败\n' + repr(eval_exc))


evaluate = Function()
evaluate.func = f_evaluation
evaluate.Mandarin_prompt = '计算'
evaluate.English_prompt = 'evaluate'
evaluate.Mandarin_help = f'''
计算一个表达式的结果
输入举例：
{sets.bot_name} 计算 3+5**2'''
evaluate.English_help = ''  # TODO
