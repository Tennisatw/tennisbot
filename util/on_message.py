import asyncio
import random
import re
import traceback
import typing
import discord

from util.config import MESSAGES
from util.info_process import info_process
from util.get_message import get_m
from util.send_message import send_m
from util.set import sets
from util.log import logs
from util.func_chat_log import history_clean


class MyClient(discord.Client):
    
    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.custom, name=str(random.choice([*globals().keys()]))))

    # 处理用户消息 - handle user message
    async def on_message(self, message):

        if message.author == self.user:
            return
        if message.guild is None:
            get_m.group = message.author.name
            get_m.group_id = message.author.id
        else:
            # get_m.guild = message.guild.name
            # get_m.guild_id = message.guild.id
            get_m.group = message.guild.name + '-' + message.channel.name
            get_m.group_id = message.channel.id
        get_m.person = message.author.name
        get_m.message_id = message.id
        if message.attachments:
            if message.attachments[0].content_type == 'image/jpeg':
                get_m.link = message.attachments[0].url
                get_m.type = 'image'
            elif message.attachments[0].content_type == 'audio/ogg':
                get_m.link = message.attachments[0].url
                get_m.type = 'voice'
            elif message.attachments[0].content_type == 'video/quicktime':
                get_m.link = message.attachments[0].url
                get_m.type = 'video'
            else:
                get_m.type = 'unknown'
        else:
            get_m.type = 'text'
            get_m.content = message.content

        if get_m.type == 'text':
            logs.logger.info('\t'.join(['gett', get_m.group, get_m.person, get_m.content]))
        # elif get_m.type == 'voice':
        #     get_m.download(get_m.link, f'{ROOT_PATH}/files/voice.ogg')
        #     voice2 = pydub.AudioSegment.from_ogg(f"{ROOT_PATH}/files/voice.ogg")
        #     voice2.export(f"{ROOT_PATH}/files/voice.wav", format="wav")
        #     get_m.content = voice_recognize(rf"{ROOT_PATH}/files/voice.wav")
        #     logs.logger.info('\t'.join(['getv', get_m.group, get_m.person, get_m.content]))
        else:
            logs.logger.info('\t'.join(['geto', get_m.group, get_m.person, get_m.type, get_m.content]))
            return

        send_m.group_id = get_m.group_id
        send_m.channel = message.channel
        send_m.client = self

        # if isinstance(message.channel, discord.VoiceChannel):
        #     voice_channels = [v_client.channel for v_client in self.voice_clients]
        #     if message.channel not in voice_channels:
        #         vc = await message.channel.connect()
        #     else:
        #         vc = None
        #         for v_client in self.voice_clients:
        #             if message.channel is v_client.channel:
        #                 vc = v_client
        #                 break
        #     if vc:
        #         vc.play(discord.FFmpegPCMAudio(f"{ROOT_PATH}/files/speak.wav"))

        if len(get_m.content) == 0:
            return

        if get_m.content[0] == '=':
            get_m.content = get_m.content[1:]
            poker_face = True
        elif '_pokerface' in get_m.group or '_pf' in get_m.group:
            poker_face = True
        else:
            poker_face = False

        if get_m.content[0] == '-':
            get_m.content = get_m.content[1:]
            history_clean()
            
        if sets.section != get_m.group:
            sets.get_config(get_m.group)

        if get_m.group == get_m.person or re.search(f'(_Tennisbot|_tb|_{sets.bot_name})', get_m.group, re.IGNORECASE):
            
            # 一对一 对话，或者群名称中含有"_" + Tennisbot的名字
            # One-to-one conversation, or the group name contains "_" + Tennisbot's name
            if re.search(f'^(Tennisbot|tb|{sets.bot_name})+$', get_m.content, re.IGNORECASE):
                await send_m.send_delete(get_m.message_id)
                await send_m.send_message(get_m.content)
                return
            else:
                content = get_m.content
        else:
            
            # 非一对一 对话
            # Non-one-to-one conversation
            if re.search(f'^(Tennisbot|tb|{sets.bot_name})+$', get_m.content, re.IGNORECASE):
                await send_m.send_delete(get_m.message_id)
                await send_m.send_message(get_m.content)
                return
            else:
                s_result = re.search(f'^Tennisbot|tb|{sets.bot_name}', get_m.content, re.IGNORECASE)
                if s_result:
                    content = get_m.content.replace(s_result.group(0), '', 1)
                else:
                    return

        for n_tb in range(sets.parallel):
            # n_tb = 0: 没有手动并行多开 - No manual parallel multi-open
            # n_tb = 1,2,3...: 手动并行多开 - Manual parallel multi-open
            # 其实本功能应该叫做串行多开，因为一个实例运行完毕之后再开另一个，但要修改的太多已经改不动了
            # Actually, this function should be called serial multi-open, 
            # for the instance runs after the previous one is finished, 
            # but it's too much to modify
            if sets.parallel == 1:
                await info_process([content, 0, poker_face, False])
            else:
                await info_process([content, n_tb + 1, poker_face, False])
            await asyncio.sleep(0.1)

    # 处理错误 - handle error
    async def on_error(self, event_method: str, *args: typing.Any, **kwargs: typing.Any):
        exc = traceback.format_exc()
        error_text = MESSAGES.get(sets.lang, {}).get("error", '')
        logs.logger.error(error_text + exc)
        await send_m.send_message(error_text + exc)
