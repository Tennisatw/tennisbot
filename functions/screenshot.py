from PIL import Image
from matplotlib.image import imsave
from numpy import array
from pymouse import PyMouse
from win32api import EnumDisplayMonitors
from win32con import SRCCOPY
from win32gui import GetWindowDC
from win32ui import CreateDCFromHandle, CreateBitmap

from classes import Function, GetMessage, SendMessage, sets


def window_capture(mouse=True):
    hwnd = 0  # 窗口的编号，0号表示当前活跃窗口
    # 根据窗口句柄获取窗口的设备上下文DC（Device Context）
    hwnd_dc = GetWindowDC(hwnd)
    # 根据窗口的DC获取mfcDC
    mfc_dc = CreateDCFromHandle(hwnd_dc)
    # mfcDC创建可兼容的DC
    save_dc = mfc_dc.CreateCompatibleDC()
    # 创建bitmap准备保存图片
    save_bit_map = CreateBitmap()

    # 获取监控器信息
    monitor_dev = EnumDisplayMonitors(None, None)
    w = monitor_dev[0][2][2]
    h = monitor_dev[0][2][3]
    save_bit_map.CreateCompatibleBitmap(mfc_dc, w, h)
    save_dc.SelectObject(save_bit_map)
    save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), SRCCOPY)
    save_bit_map.SaveBitmapFile(save_dc, r'files/screenshot.png')
    if mouse:
        im = PyMouse()
        mx, my = im.position()[0:2]
        cap = array(Image.open(r'files/screenshot.png'))
        cap[my - 8:my + 8, mx - 8:mx + 8, 0:2] = 0
        cap[my - 8:my + 8, mx - 8:mx + 8, 0] = 255
        cap[my - 6:my + 6, mx - 6:mx + 6, 1] = 255
        cap[my - 4:my + 4, mx - 4:mx + 4, 2] = 255
        cap[my - 2:my + 2, mx - 2:mx + 2, 0] = 0
        imsave(r'files/screenshot.png', cap)


async def f_screenshot(get_m: GetMessage, send_m: SendMessage, text):
    if text[2] == '隐藏鼠标' or text[2] == 'hidemouse':
        window_capture(False)
    else:
        window_capture()
    send_m.type = 2
    await send_m.send(r'files/screenshot.png')


screenshot = Function()
screenshot.func = f_screenshot
screenshot.developer_only = True
screenshot.Mandarin_prompt = '截屏'
screenshot.English_prompt = 'screenshot'
screenshot.Mandarin_help = f'''
发送{sets.bot_name}所在的电脑屏幕的截屏
如附加”隐藏鼠标“，则会在截屏中把鼠标隐藏'''
screenshot.English_help = f'''
Send a screenshot of the computer that running {sets.bot_name}
If "hidemouse" is added, the mouse will be hidden in the screenshot'''
