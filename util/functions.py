import builtins
import json
import random
import re
import time
from urllib import parse

import bs4
import requests
import wikipedia

from util.config import MESSAGES, ROOT_PATH
from util.set import sets
from util.log import logs
from util.get_message import get_m


def bot_set(param):
    setting = param[0]
    value = param[1]
    text_success = MESSAGES.get(sets.lang, {}).get("set_success", '').format(setting=setting, value=value)
    text_failed = MESSAGES.get(sets.lang, {}).get("set_failed", '').format(setting=setting)

    if (setting == 'bot_name') or (setting == '昵称'):
        sets.bot_name = value
        sets.set_config(get_m.group)
    elif (setting == 'chat_model') or (setting == '聊天模型'):
        if value in ['mini', 'full']:
            sets.chat_model = value
            sets.set_config(get_m.group)
        else:
            logs.logger.warning(f'{setting}设置失败 - Failed to set {setting}')
            return text_failed
    elif (setting == 'chat_temperature') or (setting == '聊天热度'):
        sets.chat_temperature = value
        sets.set_config(get_m.group)
    elif (setting == 'language') or (setting == '语言'):
        if value == 'zh-CN':
            sets.lang = 'zh-CN'
            sets.set_config(get_m.group)
        elif value == 'en-US':
            sets.lang = 'en-US'
            sets.set_config(get_m.group)
        elif value in ['zh', 'zh-TW', 'Chinese', 'chinese', '中文', '汉语', '汉']:
            logs.logger.warning(f'请使用"zh-CN"，而不是{value} - please use "zh-CN" instead of {value}')
            sets.lang = 'zh-CN'
            sets.set_config(get_m.group)
        elif value in ['en', 'en-UK', 'en-GB', 'en-CA', 'English', '英语']:
            logs.logger.warning(f'请使用"en-US"，而不是{value} - please use "en-US" instead of {value}')
            sets.lang = 'en-US'
            sets.set_config(get_m.group)
        else:
            logs.logger.warning(f'{setting}设置失败 - Failed to set {setting}')
            return text_failed
    elif (setting == 'parallel_number') or (setting == '并行数量'):
        sets.parallel = int(value)
        sets.set_config(get_m.group)

    else:
        return MESSAGES.get(sets.lang, {}).get("no_setting_option", '').format(setting=setting, bot_name=sets.bot_name)
    return text_success


def _time_recognize(time_data):
    if "-" in time_data:
        time_p = re.search(r"^(\d?)-(\d+)[:∶：](\d+)$", time_data)
        day = int(time_p.group(1))
        if day == 0:
            day = 7
        time_str = str(day) + "-"
    else:
        time_p = re.search(r"^(d?)(\d+)[:∶：](\d+)$", time_data)
        time_str = ""
    hour = int(time_p.group(2))
    if hour >= 24:
        hour -= 24
    minute = int(time_p.group(3))
    time_str = time_str + str(hour).zfill(2) + ":" + str(minute).zfill(2)
    return time_str


def alarm_set(param):
    time_data = param[0]
    if len(param) > 1:
        info = param[1]
    else:
        info = ""

    try:
        time_str = _time_recognize(time_data)
    except (ValueError, AttributeError):
        return MESSAGES.get(sets.lang, {}).get("add_alarm_failed", '').format(time_data=time_data)

    if time_str in sets.schedule.alarm:
        return MESSAGES.get(sets.lang, {}).get("add_alarm_exist", '').format(time_str=time_str)
    else:
        sets.schedule.alarm[time_str] = info
        sets.schedule.set_config()
        return MESSAGES.get(sets.lang, {}).get("add_alarm_success", '').format(time_str=time_str, info=info)


def alarm_delete(param):
    time_data = param[0]
    try:
        time_str = _time_recognize(time_data)
    except (ValueError, AttributeError):
        return MESSAGES.get(sets.lang, {}).get("cancel_alarm_failed", '').format(time_data=time_data)

    if time_str not in sets.schedule.alarm:
        return MESSAGES.get(sets.lang, {}).get("cancel_alarm_exist", '').format(time_str=time_str)
    else:
        info = sets.schedule.alarm[time_str]
        sets.schedule.alarm.pop(time_str)
        sets.schedule.set_config()
        return MESSAGES.get(sets.lang, {}).get("cancel_alarm_success", '').format(time_str=time_str, info=info)


def alarm_get():
    if sets.schedule.alarm:
        alarm_result = "\n".join(f"{time_str} {info}" for time_str, info in sets.schedule.alarm.items())
        return MESSAGES.get(sets.lang, {}).get("alarm_get", '').format(alarm_result=alarm_result)
    else:
        return MESSAGES.get(sets.lang, {}).get("alarm_get_none", '')


def get_location():
        r = requests.get("http://httpbin.org/ip")
        ip = json.loads(r.text)["origin"]

        url = f"http://ip-api.com/json/{ip}?fields=message,country,regionName,city,lat,lon,timezone&lang={sets.lang}"
        res = requests.get(url)

        data: dict = json.loads(res.text)
        return data["city"]


def get_weather(param=[]):
    def translate(text_t, to_lang="zh-CN", text_lang="en-US"):
        if to_lang != text_lang:
            text_t = parse.quote(text_t)
            url = f"http://translate.google.com/m?q={text_t}&tl={to_lang}&sl={text_lang}"
            expr = r'(?s)class="(?:t0|result-container)">(.*?)<'
            return re.findall(expr, requests.get(url).text)[0]
        else:
            return text_t

    if len(param) > 0:
        location = param[0]
        if location == 'local':
            location = get_location()
    else:
        location = get_location()
    
    if len(param) > 1:
        days = int(param[1])
    else:
        days = 1

    if any(map(lambda c: "\u4e00" <= c <= "\u9fa5", location)):
        location = translate(location, "en-US", "zh-CN")

    api_key = "c206fe85eb184f9384215136230606"
    weather_url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days={days}"
    response = requests.get(weather_url)

    if response.status_code == 200:
        weather_data = response.json()
        city = weather_data['location']['name']
        region = weather_data['location']['region']
        country = weather_data['location']['country']
        text = MESSAGES.get(sets.lang, {}).get("weather_forcast", '').format(
            city=translate(city, sets.lang, "en-US"), 
            region=translate(region, sets.lang, "en-US"), 
            country=translate(country, sets.lang, "en-US"), 
            days=days
        )
        
        forecast_data = weather_data["forecast"]["forecastday"]
        for day in forecast_data:
            date = day["date"]
            condition = day["day"]["condition"]["text"]
            max_temp = day["day"]["maxtemp_c"]
            min_temp = day["day"]["mintemp_c"]
            humidity = day["day"]["avghumidity"]
            text = text + MESSAGES.get(sets.lang, {}).get("weather_day", '').format(
                date=date, 
                condition=translate(condition, sets.lang, "en-US"), 
                max_temp=max_temp, 
                min_temp=min_temp, 
                humidity=humidity
            )
    else:
        return MESSAGES.get(sets.lang, {}).get("weather_get_failed", '')

    return text


def get_time():
    return time.strftime("%Y/%m/%d %H:%M:%S %A")


def raise_error(param):
    error_name = param[0]
    error_text = param[1] if len(param) > 1 else ""
    try:
        error = getattr(builtins, error_name)
        if isinstance(error(), BaseException):
            raise error(error_text)
        else:
            raise Exception(error_text + " " + error_name)
    except AttributeError:
        raise Exception(error_text + " " + error_name)


def soviet_joke(param=["0"]):
    if len(param) > 0:
        num = param[0]
    else:
        num = "0"
    if num == "0":
        num = str(random.randint(1, 290))
    joke_file = open(f"{ROOT_PATH}/files/soviet_joke.txt", "r", encoding="UTF-8")
    joke = joke_file.read().split(num + "、\n")[1].split(str(int(num) + 1))[0]
    joke_file.close()
    return joke


def search_website(param):
    """Search the web"""
    query = param[0]
    api_key = "AIzaSyBKmJlj8e0P2Nf7sMN5WLI9iVsSp6jI56Y"
    cx = "10216c2365e40494b"
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={query}"

    response = requests.get(url).json()
    result = ""
    for item in response["items"]:
        result = result + item["title"] + " " + item["link"] + "\n"

    return result


def get_website(param):
    """Get the content of a website"""
    url = param[0]
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/89.0.4389.114 Safari/537.36 "
    }
    req = requests.get(url=url, headers=headers)
    req.encoding = "utf-8"

    html = req.text
    soup = bs4.BeautifulSoup(html, "html.parser")
    result = re.sub("\n+", "\n", soup.text)
    return result


def wiki(param):
    prompt = param[0]
    if sets.lang == "zh-CN":
        wikipedia.wikipedia.set_lang("zh")
    else:
        wikipedia.wikipedia.set_lang("en")

    wiki_search = wikipedia.wikipedia.search(prompt)
    try:
        result = wikipedia.wikipedia.summary(wiki_search[0])
    except wikipedia.wikipedia.DisambiguationError as dae:
        result = wikipedia.wikipedia.summary(random.choice(dae.options))

    return MESSAGES.get(sets.lang, {}).get("wiki_search", '').format(
        wiki_search=wiki_search, result=result
    )
