from time import sleep
from pymouse import PyMouse

from classes import Function, GetMessage, SendMessage, sets


def mouse_c(text):
    try:
        im = PyMouse()
        x = im.position()[0]
        y = im.position()[1]
        if text[2] == '位置':
            return str(x) + ' ' + str(y)
        elif text[2] == '滚动':
            if text[3] == '':
                a = 0
            else:
                a = -int(text[3])
            if text[4] == '':
                b = 0
            else:
                b = int(text[4])
            im.scroll(a, b)
            return '鼠标操作成功'
        else:
            if text[3] != '':
                x = int(text[3])
            if text[4] != '':
                y = int(text[4])
            if text[5] != '':
                loop = int(text[5])
            else:
                loop = 1
            if text[2] == '移动':
                im.move(x, y)
                return '鼠标操作成功'
            elif text[2] == '点击':
                for _ in range(loop):
                    im.click(x, y, 1)
                    sleep(0.1)
                return '鼠标操作成功'
            elif text[2] == '右键点击':
                for _ in range(loop):
                    im.click(x, y, 2)
                    sleep(0.1)
                return '鼠标操作成功'
            elif text[2] == '中键点击':
                for _ in range(loop):
                    im.click(x, y, 3)
                    sleep(0.1)
                return '鼠标操作成功'
        return '鼠标模块没有此功能'
    except Exception as exc:
        return '鼠标操作失败\n' + repr(exc)


async def f_mouse(get_m: GetMessage, send_m: SendMessage, text):
    await send_m.send(mouse_c(text))


mouse = Function()
mouse.func = f_mouse
mouse.developer_only = True
mouse.Mandarin_prompt = '鼠标'
mouse.English_prompt = 'mouse'
mouse.Mandarin_help = f'''
操纵{sets.bot_name}所在的电脑的鼠标
共有以下几种操作：点击、右键点击、中键点击、移动、滚动、位置
其中，各功能的输入格式为：
点击、右键点击、中键点击；
{sets.bot_name} 鼠标 鼠标操作 (x位置) (y位置) (点击次数)
移动；
{sets.bot_name} 鼠标 移动 (x位置) (y位置)
滚动；
{sets.bot_name} 鼠标 滚动 (向下滚动的距离) (向右滚动的距离)
位置：发送鼠标当前的位置
注：开发者电脑的显示屏尺寸为1920*1080，左上角为(0,0)，右上角为(1920,0)
输入举例：
{sets.bot_name} 鼠标 位置
{sets.bot_name} 鼠标 点击 50 500 3
{sets.bot_name} 鼠标 移动 1300 10
{sets.bot_name} 鼠标 滚动 1 0'''
mouse.English_help = ''' '''  # TODO
