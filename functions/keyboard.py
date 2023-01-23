from re import search, match
from time import sleep
from pykeyboard import PyKeyboard

from classes import Function, GetMessage, SendMessage, sets


class FindKeyError(Exception):
    new_repr = f'can not find the key/cy'

    def set_repr(self):
        Exception.__init__(self, self.new_repr)


def keyboard_c(text):
    try:
        ik = PyKeyboard()

        def key_reform(key_name):
            if len(key_name) == 1:
                return key_name
            elif key_name == 'and':
                key = '&'
            elif key_name == 'ctrl':
                key = ik.control_key
            elif key_name == 'esc':
                key = ik.escape_key
            elif (key_name == 'win') or (key_name == 'windows'):
                key = ik.windows_l_key
            elif key_name == 'caps&lock':
                key = ik.caps_lock_key
            elif key_name[0] == 'f':
                function_num_a = match('f[0-9]+', key_name)
                function_num = int(function_num_a.string.split('f')[1])
                key = ik.function_keys[function_num]
            else:
                try:
                    key = eval('ik.' + key_name + '_key')
                except AttributeError:
                    a_error = FindKeyError()
                    a_error.new_repr = f'can not find the key "{key_name}" /cy'
                    a_error.set_repr()
                    raise a_error
            return key

        if text[2] == '输入':
            ik.type_string(text[3])
            return '键盘操作成功'
        elif text[2] == '按下':
            try:
                loop = int(text[4])
            except ValueError:
                loop = 1
            for _ in range(loop):
                if search('&', text[3]) is not None:
                    key_list = []
                    key_list_A = text[3].split('&')
                    for keys in key_list_A:
                        key_list.append(key_reform(keys))
                    ik.press_keys(key_list)
                else:
                    keys = key_reform(text[3])
                    ik.tap_key(keys)
                sleep(0.1)
            return '键盘操作成功'
        elif text[2] == '长按':
            ik.press_key(key_reform(text[3]))
            return '键盘操作成功'
        elif text[2] == '释放':
            ik.release_key(key_reform(text[3]))
            return '键盘操作成功'
        return '键盘模块没有此功能'
    except Exception as exc:
        return '键盘操作失败\n' + repr(exc)


async def f_keyboard(get_m: GetMessage, send_m: SendMessage, text):
    await send_m.send(keyboard_c(text))


keyboard = Function()
keyboard.func = f_keyboard
keyboard.developer_only = True
keyboard.Mandarin_prompt = '键盘'
keyboard.English_prompt = 'keyboard'
keyboard.Mandarin_help = f'''
操纵{sets.bot_name}所在电脑的键盘
共有以下几种操作：
输入：输入字符串
按下：按下并松开某几个按键，可以设定按下次数，默认是1次
如要按下多个键，键与键之间用&连接，如想要输入&请用and代替
长按：按住某个按键，直到释放它
释放：释放这个按住的按键
利用字母和数字确定按键，如H e 0
利用小写字母(简称或全称)确定功能键，支持的简称包括:
alt ctrl shift win backspace esc enter 
up down left right space capslock f1-f12 
输入格式：
{sets.bot_name} 键盘 键盘操作 键名(&键名2(&键名3…)) (按下次数)
输入举例：
{sets.bot_name} 键盘 输入 1f1e33
{sets.bot_name} 键盘 按下 ctrl&p 2
{sets.bot_name} 键盘 长按 alt'''
keyboard.English_help = ''''''  # TODO
