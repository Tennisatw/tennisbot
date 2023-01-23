from re import search
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, audio
from pydub import AudioSegment

from classes import Function, GetMessage, SendMessage, sets


def speak_c(text, style='', pitch=0, rate=0, volume=0, send=True, play=False, reverse=False, lang='zh-CN'):
    text = text.replace('🥎', 'tennis bot')
    if pitch >= 0:
        pitch = '+' + str(pitch)
    if rate >= 0:
        rate = '+' + str(rate)
    if volume >= 0:
        volume = '+' + str(volume)

    while search('↗', text) is not None:
        res = search('(↗+)', text)
        modify_n = len(res.group(1)) * 25
        text_list = text.split(res.group(1), 1)
        text_m = text_list[0][-1]
        text = text_list[0][:-1] + f'<prosody pitch="+{modify_n}%" >' + text_m + '</prosody>' + text_list[1]

    while search('↘', text) is not None:
        res = search('(↘+)', text)
        modify_n = len(res.group(1)) * 25
        text_list = text.split(res.group(1), 1)
        text_m = text_list[0][-1]
        text = text_list[0][:-1] + f'<prosody pitch="-{modify_n}%" >' + text_m + '</prosody>' + text_list[1]

    while search('~', text) is not None:
        res = search('(~+)', text)
        modify_n = len(res.group(1)) * 20
        text_list = text.split(res.group(1), 1)
        text_m = text_list[0][-1]
        text = text_list[0][:-1] + f'<prosody rate="-{modify_n}%" >' + text_m + '</prosody>' + text_list[1]

    while search('\|', text) is not None:
        text = text.replace('|', '<break time="200" />', 1)
    if lang == 'zh-CN':
        ssml1 = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
               xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="zh-CN">
            <voice name="zh-CN-XiaohanNeural">'''
    else:
        ssml1 = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
                xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
            <voice name="en-US-SaraNeural">'''
    ssml2 = f'<mstts:express-as style="{style}" styledegree="1">'
    ssml3 = f'<prosody pitch="{pitch}%" rate="{rate}%" volume="{volume}%">'
    ssml4 = text
    ssml5 = '''</prosody>
            </mstts:express-as>
        </voice>
    </speak>'''
    ssml = ssml1 + ssml2 + ssml3 + ssml4 + ssml5

    speech_config = SpeechConfig(
        subscription='bdb82bca1ed3420492e20e6010a17ab0',
        region='canadacentral')
    if play:
        audio_config = audio.AudioOutputConfig(
            use_default_speaker=True, )
        speech_synthesizer = SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config)
        speech_synthesizer.speak_ssml_async(ssml).get()

    if send:
        audio_config = audio.AudioOutputConfig(
            use_default_speaker=True, filename='files/speak.wav')
        speech_synthesizer = SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config)
        speech_synthesizer.speak_ssml_async(ssml).get()
        audio_config = audio.AudioOutputConfig(
            use_default_speaker=True, filename='files/speak2.wav', )
        speech_synthesizer = SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config)

        if reverse:
            song = AudioSegment.from_wav('files/speak.wav')
            backwards = song.reverse()
            backwards.export('files/speak.wav', 'wav')

        return 'files/speak.wav'


async def f_speak(get_m: GetMessage, send_m: SendMessage, text):
    pitch = 0
    rate = 0
    volume = 0
    reverse = False
    for parameter in text[3:]:
        if '=' in parameter:
            if parameter.split('=')[0] == '音调':
                try:
                    pitch = int(parameter.split('=')[1])
                except ValueError:
                    pass
            elif parameter.split('=')[0] == '语速':
                try:
                    rate = int(parameter.split('=')[1])
                except ValueError:
                    pass
            elif parameter.split('=')[0] == '音量':
                try:
                    volume = int(parameter.split('=')[1])
                except ValueError:
                    pass
            else:
                pass
        if parameter == '倒放':
            reverse = True
    speak_c(text=text[2], pitch=pitch, rate=rate, volume=volume, reverse=reverse, lang=get_m.lang)

    send_m.type = 3
    await send_m.send(r'files/speak.wav')


speak = Function()
speak.func = f_speak
speak.Mandarin_prompt = '说话'
speak.English_prompt = 'speak'
speak.Mandarin_help = f'''
使{sets.bot_name}说出一段话
如附加一些参数可使得{sets.bot_name}用不同的语速，音调，音量来说话，或者是倒放
语速，音调，和音量的范围是-100~+100
在一个字的后面加上↗、↘、~、|可以使得这个字升调、降调、延长，以及在这个字后面停顿
符号可以多次重复，以增强效果。但前三种符号不可对同一个字混用。
输入格式：
{sets.bot_name} 说话 说话内容 (参数1) (参数2)…
输入举例
{sets.bot_name} 说话 Helloworld 语速=-50
{sets.bot_name} 说话 我去，初音未来 语速=30 音调=10 音量=100 倒放
{sets.bot_name} 说话 到↗达↗世↗界↗最↗高↗城↗，理~~塘↗！太美丽啦理塘，哎呀这不丁↗真↗吗？再|看一下远处的雪山吧家人们↘↘ 语速=-10
{sets.bot_name} 说话 大~好，我是欧头 倒放'''
speak.English_help = ''  # TODO
