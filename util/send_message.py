import configparser

import discord
import requests

from util.config import ROOT_PATH
from util.log import logs


class SendMessage:
    """
    异步向Discord频道发送消息、照片和语音消息。
    send messages, photos, and voice messages to a Discord channel asyncly.
    """
    def __init__(self, client=None, channel=None, voice_mode=False):
        self.client = client
        self.channel = channel
        self.voice_mode = voice_mode
        self.group_id = ''

    async def send_message(self, content=''):
        try:
            logs.logger.info('\t'.join(['send_message', content]))
            if len(content) > 1000:
                content_list = [content[i:i + 1000] for i in range(0, len(content), 1000)]
                result = None
                for cont in content_list:
                    result = await self.channel.send(cont)
                return result
            else:
                return await self.channel.send(content)
        except Exception as e:
            logs.logger.error(f"send_message出现了一个错误: An error occurred in send_message: {repr(e)}")

    async def send_photo(self, content=''):
        try:
            logs.logger.info('\t'.join(['send_photo', content]))
            return await self.channel.send(file=discord.File(content))
        except Exception as e:
            logs.logger.error(f"send_photo出现了一个错误: An error occurred in send_photo: {repr(e)}")
            raise

    async def send_voice(self, content=''):
        try:
            logs.logger.info('\t'.join(['send_voice', content]))
            return await self.channel.send(file=discord.File(content))
        except Exception as e:
            logs.logger.error(f"send_voice出现了一个错误: An error occurred in send_voice: {repr(e)}")
            raise

    async def send_document(self, content=''):
        try:
            logs.logger.info('\t'.join(['send_document', content]))
            return await self.channel.send(file=discord.File(content))
        except Exception as e:
            logs.logger.error(f"send_document出现了一个错误: An error occurred in send_document: {repr(e)}")
            raise

    async def send_thinking(self, content=''):
        logs.logger.info('\t'.join(['send_thinking', content]))
        return await self.channel.send(content)

    async def send_delete(self, message_id=0):
        msg = await self.channel.fetch_message(message_id)
        logs.logger.info('\t'.join(['send_delete']))
        try:
            await msg.delete()
        except discord.Forbidden:
            pass


def send_sync(content, chat_id=0):
    """
    同步发送消息到Discord频道
    Send message to discord channel
    """
    try:
        bot_config = f'{ROOT_PATH}/files/bot_config.ini'
        config = configparser.ConfigParser()
        config.read(bot_config, encoding='utf-8')
        
        if not config.has_section('TOKENS'):
            raise ValueError("bot_config.ini缺少TOKENS部分 - Missing TOKENS section in bot_config.ini")
            
        discord_token = config.get('TOKENS', 'discord', fallback=None)
        if not discord_token:
            raise ValueError("bot_config.ini缺少discord token - Missing discord token in bot_config.ini")
            
        discord_token = 'Bot ' + discord_token
        
        if chat_id == 0:
            chat_id = config.get('TOKENS', 'discord_default_chat_id', fallback=None)
            if not chat_id:
                raise ValueError("bot_config.ini缺少discord_default_chat_id - Missing discord_default_chat_id in bot_config.ini")
                
        url = f'https://discord.com/api/v10/channels/{chat_id}/messages'
        auth = {'authorization': discord_token}
        msg = {'content': content}
        
        response = requests.post(url=url, headers=auth, data=msg)
        response.raise_for_status()
        
        logs.logger.info('\t'.join(['send', 'sync', content]))
        return response
        
    except Exception as e:
        logs.logger.error(f"send_sync出现了一个错误: An error occurred in send_sync: {repr(e)}")


send_m = SendMessage()