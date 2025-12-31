2025.12.15:

创建仓库，新建初始文件
创建环境：

    uv init
    uv add openai-agents
    .\.venv\Scripts\activate

<br>

2025.12.16:

    uv add python-dotenv

<br>

2025.12.20:

为了以后支持的时长更久，打算切换到python3.13

删除.venv，.python-version，pyproject.toml，uv.lock

    uv python install 3.13
    uv init
    uv venv
    .venv\Scripts\activate
    uv add openai-agents
    uv add python-dotenv
    uv add pytest

完善了Tennisbot的架构构想（见z/dev_thoughts.md）

创建了developer agent的草稿

<br>

2025.12.28:

编写了AGENT.md，作为Tennisbot的prompt基础
完善了main.py，src/agent.py的基础架构。
现在可以启动Tennisbot并与她对话。

<br>

2025.12.29:

添加了联网搜索功能
编写了以下tools：
    - read_file：读取文件内容
    - list_files：列出目录结构
    - grep：在文件中搜索关键词
    - apply_patch：应用代码补丁
完善了developer sub-agent的功能
现在Tennisbot可以通过developer sub-agent修改自己的代码了。

又编写了 write_file 工具，用于直接写文件内容，用于补丁失败时的兜底方案。

<br>

2025.12.30:

修改了patch逻辑，因为旧的apply_patch失败率太高。
将其拆分成了2个工具：
    - draft_patch：生成git-styled patch
    - apply_patch（新）：应用git-styled patch
此外，也放松了git apply --check的检查："--recount"

    uv add pytest-asyncio