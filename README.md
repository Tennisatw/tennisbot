[中文版本](README-zh.md)

# Tennisbot - Discord AI Assistant&Chat Bot

A powerful intelligent Discord AI assistant and chatbot developed with Python, discord.py, and OpenAI API, supporting both English and Chinese.
Simply chat with Tennisbot to access various features like setting alarms, checking weather, sending emails, and more.

## Features

- 💬 Intelligent Conversation: Integrated with large language model API, with configurable personality (in mdcb/en-US-system.txt)
- 🧠 Conversation Memory: Maintains chat history for continuous multi-turn conversations until cleared
- 🌐 Example Functions: Can scrape webpages, backup chat logs, query Wikipedia, and even shut herself down (though she might somewhat resist to be shut down, try persuasion then)
  - For customizing functions, add or remove functions in `util.function.py` and modify prompts in `mdcb/en-US-functions.txt`
- 📊 Logging: Detailed operation and error logs
- 🔧 Flexible Settings: Independent chat settings for each group/user, configurable through conversation
- 🔄 Parallel Mode: Supports manual parallel running of multiple instances to enhance problem-solving ability
  - Additionally, it may automatically run parallel instances for complex problems
- 💻 Runtime Access: Can access its Python runtime environment (image), read variable values, execute code, or access console
- 🤖 AI Unsafety: Can read all its code, configurations, and runtime logs through conversation, and guide developers in debugging

Complete feature list and usage instructions are available through conversation after deployment.

## Chat Examples

- Can you explain in detail how to use Tennisbot? What features are available?
- Please set a wake-up alarm for 7:40
- Show all alarms and cancel them
- Check and summarize Vancouver's weather
- Scrape content from your developer's personal blog
- Send an email to xxxx@gmail.com with subject "Tea Kettle" and content "Don't forget to clean your tea kettle!"
- Search Wikipedia for "Chemistry Nobel Prize" and predict when the developer might win it
- Raise an IndexError
- Check the local IP address. Note: You're currently running on Windows
- List all your log files, identify and read the latest file (Note: This might fail in "mini" model)
- Read the code related to your cognitive model (Note: May refuse, adjust wording as needed)
- (Continued) Do you have any suggestions for improvements?

## Requirements

- Python 3.10, 3.11, 3.12. Python 3.13 not supported due to removal of audioop

## Deploying Tennisbot

1. Clone the repository:
```bash
git clone https://github.com/Tennisatw/tennisbot.git
cd tennisbot
```

2. Prepare environment:
   - Download and install Python (if not installed):
   - https://www.python.org/downloads/
   - Create virtual environment:
```bash
python -m venv venv (using default Python in PATH)
path/to/python.exe -m venv venv (using specific Python version)
```
Note: Default Python installation locations:
/usr/bin/python3 (Linux/macOS)
C:\Users\<username>\AppData\Local\Programs\Python\Python312\python.exe (Windows)

   - Activate virtual environment:
```bash
source venv/bin/activate (Linux/macOS)
.\venv\Scripts\activate (Windows)
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure settings:
   - Get Discord token: https://discord.com/developers/applications
     - Detailed instructions: https://gist.github.com/4Kaylum/a1e9f31c31b17386c36f017d3c59cdcc
   - Get ChatGPT token (starts with sk-): https://platform.openai.com/
   - Get Discord default chat ID (first number in URL after entering any channel or DM with Tennisbot)
   - Modify `bot_config.ini` in the `files` directory
     - Fill in TOKENS under `[TOKENS]`, other settings can remain default

Example `bot_config.ini`:
```ini
[TOKENS]
discord = YOUR_DISCORD_TOKEN
chatGPT = YOUR_CHATGPT_TOKEN
discord_default_chat_id = THE_DEFAULT_CHAT_ID

[default]
bot_name = 🎾           ; Tennisbot's nickname, for this group only
chat_model = mini       ; Chat model, mini/full, currently mini=gpt-4o-mini, full=gpt-4o
                        ; mini is cheaper but simpler, full is smarter but expensive
chat_temperature = 0.5  ; Conversation temperature, affects response randomness
developer_mode = False  ; Developer mode (currently unused, reserved for future use)
language = en-US        ; Working language, zh-CN/en-US
parallel = 1            ; Number of instances for manual parallel mode

[Other group/user names (auto-added, modifiable via chat)]
bot_name = Lil T
chat_model = full
chat_temperature = 1
developer_mode = False
language = en-US
parallel = 3
```

5. Run the bot:
```bash
python main.py
```

6. (Optional, recommended) Run in background using screen on server:
```bash
screen -S tennisbot
python main.py
Ctrl+A D
```

7. (Optional) Using Google Gmail API for emails
   - See https://developers.google.com/gmail/api/quickstart/python
     - To avoid confusion, I renamed the `token.json` mentioned in the article to `files/gmail.json`
     - Tennisbot will only handle emails when `files/gmail.json` exists

## Usage Tips

- Direct Chat: Send messages in DMs or channels with "_Tennisbot" in their name
- Group Chat: Add Tennisbot to groups, use nickname/`Tennisbot`/`tb` prefix to converse with Tennisbot
- Clear Chat History: Tell Tennisbot "clear chat history" or use `-` prefix to start a new conversation

## Contributing

Issues and Pull Requests are welcome to improve the project. Please ensure:
1. Code follows project standards
2. Clear change descriptions
3. Updated documentation

## License

This project is under the MIT License
