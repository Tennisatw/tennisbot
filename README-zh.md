[English Version](README.md)

# Tennisbot - Discord AI 助手&聊天机器人

一个功能强大的智能Discord AI助手和聊天机器人，基于Python、discord.py和OpenAI API开发，支持中英文。
仅需通过与Tennisbot对话，即可使用各种功能，如设置闹钟，查询天气，收发邮件等等

## 功能特性

- 💬 智能对话：接入大语言模型API，且支持配置个性化人格（在mdcb/zh-CN-system.txt中）
- 🧠 记忆对话：支持记忆聊天记录，在清理聊天记录前，可以持续多轮对话
- 🌐 示例功能：可以抓取网页，备份聊天记录，查询wiki百科，以及让自己关机（但她可能会抗拒关机，可能需要劝劝）
  - 支持自行在`util.function.py`中删除或添加新功能，并在`mdcb/zh-CN-functions.txt`中修改提示词
- 📊 日志记录：详细的操作和错误日志
- 🔧 灵活设置：每个群组/用户可以有独立的聊天设置，且仅通过对话即可完成所有设置
- 🔄 多开模式：支持手动并行运行多个实例，增强解决复杂问题的能力
  - 除此之外，在遇到复杂问题时，她也可能自动并行运行多个实例
- 💻 访问运行环境：支持访问自身的python运行环境（的镜像），读取变量值，并执行代码，或访问控制台
- 🤖 智械危机：仅通过对话即可使其读取自身所有的代码，配置和运行日志，并指导开发者如何debug

完整的功能列表及使用说明可在部署后通过对话获取。

## 一些对话示例

- 请详细地介绍怎么使用Tennisbot？都有什么功能？
- 请设置一个7：40的起床闹钟
- 请查询所有闹钟，并取消它们
- 请查询温哥华的天气，并总结
- 请爬取你的开发者的个人博客上的内容
- 请给xxxx@qq.com发送一封邮件，标题为“刷茶壶”，内容为“别忘了刷你的茶壶！”
- 请在维基百科中查询“化学诺奖”页面，并简单预测开发者什么时候可以获奖
- 报一个IndexError
- 请查询本机ip地址。注意：你当前暂时运行在windows上
- 请列出你的所有log文件，判断并读取最新的文件（注：此对话在"mini"模型下可能会失败）
- 请你读取有关你的心智模型的代码（注：有一定概率会拒绝提供，可以适当调节用词）
- （接上）你有什么修改意见吗？

## 安装要求

- Python 3.10, 3.11, 3.12。Python3.13由于移除了audioop故不支持

## 部署Tennisbot

1. 克隆仓库：
```bash
git clone https://github.com/Tennisatw/tennisbot.git
cd tennisbot
```

2. 准备环境：
   - 下载并安装python（如果没有的话）：  
   - https://www.python.org/downloads/  
   - 创建虚拟环境：
```bash
python -m venv venv （如果使用环境变量中默认的python）
path/to/python.exe -m venv venv （如果使用某特定版本的python）
```
注：python的默认安装位置为：  
/usr/bin/python3 （linux/macOS）  
C:\Users\<用户名>\AppData\Local\Programs\Python\Python312\python.exe （windows）  

   - 激活虚拟环境：
```bash
source venv/bin/activate （linux/macOS）
.\venv\Scripts\activate （windows）
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置文件设置：
   - 获得discord token：https://discord.com/developers/applications
     - 这篇文章有详细说明：https://gist.github.com/4Kaylum/a1e9f31c31b17386c36f017d3c59cdcc
   - 获得chatGPT token (以sk-开头)：https://platform.openai.com/
   - 获得discord default chat id（进入discord服务器的任意频道后，或者进入与Tennisbot的私聊后，网址中的第一个数字）
   - 在 `files` 目录下，修改 `bot_config.ini`
     - 在 `[TOKENS]` 中填入上述TOKEN，其他配置项可以设成默认

`bot_config.ini`配置示例：
```ini
[TOKENS]
discord = YOUR_DISCORD_TOKEN
chatGPT = YOUR_CHATGPT_TOKEN
discord_default_chat_id = THE_DEFAULT_CHAT_ID

[default]
bot_name = 🎾           ; Tennisbot的昵称，仅限本群使用
chat_model = mini       ; 聊天模型，mini/full，目前mini为gpt-4o-mini，full为gpt-4o
                        ; mini便宜却笨，full聪明但贵
chat_temperature = 0.5  ; 对话温度，影响回复的随机性
developer_mode = False  ; 开发者模式（目前未启用，预留以备将来使用）
language = zh-CN        ; 工作语言，zh-CN/en-US
parallel = 1            ; 手动并行多开模式的实例数

[其他群名或用户名（自动添加，可在对话中修改）]
bot_name = 小T
chat_model = full
chat_temperature = 1
developer_mode = False
language = zh-CN
parallel = 3
```

5. 运行机器人：
```bash
python main.py
```
注：运行机器人的平台需可以科学上网，因为需要访问Discord API  
如有国内支持免费API的，文档健全的聊天应用平台，请联系开发者

6. （可选，推荐）在服务器中使用screen后台运行：
```bash
screen -S tennisbot
python main.py
Ctrl+A D
```

7. （可选）使用google gmail api收发邮件
   - 见 https://developers.google.com/gmail/api/quickstart/python
     - 以防混淆，我将文章中的`token.json`重命名为`files/gmail.json`
     - 只有当`files/gmail.json`存在时，Tennisbot才会收发邮件

## 使用要点

- 直接对话：在私聊中，或者名字带有“_Tennisbot”的频道中直接发送消息
- 群组对话：将Tennisbot拉到群组中，在群组中使用 其昵称/`Tennisbot`/`tb` 前缀唤起Tennisbot对话
- 清除聊天记录：通过聊天告诉Tennisbot“清除聊天记录”，或者使用 `-` 前缀开始新对话

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目。请确保：
1. 代码符合项目规范
2. 提供清晰的改动说明
3. 更新相关文档

## 许可证

本项目使用 MIT License
