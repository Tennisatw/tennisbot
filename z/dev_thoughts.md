尽量使用我自己/Tennisbot自己开发，尽量不使用其他。

<br>

Tennisbot应该有的架构：

- start.bat：启动脚本，依据返回值决定结束/更新并重启。
- main.py：Tennisbot的启动文件。
- src：Tennisbot的核心代码和核心文件。
    - agent.py：主agent的实现代码。
    - settings.json：设置文件的json版本，供Tennisbot自己读取。
    - tools：工具，每个工具单独放一个文件。
        - (tool-name).py：工具脚本，包含一些简单常用的功能函数。
        可能有的tools包括：
        - setting：修改/更新settings.json的工具。
        - diary：读取/添加日记。
            - 记录所有需要记的东西
            - 每天从聊天记录中总结需要记的东西
        
    - agents：除了主agent之外的副agent，每个agent单独放一个文件夹。
        - (agent-name)：
            - agent.json：技能的说明文档，当加载技能的时候应该先读取这个文件。
            - (tool-name).py：工具脚本，包含此skills中常用的功能函数。（考虑和并到主tools中？）
            - 以及一些此agent会使用的文件。
        可能有的agents包括：
        - developer：开发自身！
        - 通过MCP操控chrome浏览器，完成一些自动化任务。
        - 通过MCP操控我的电脑。
        - 文章知识库创建与查询？
    - AGENT.md：供Tennisbot自己阅读的文档，里面的内容应短小精悍，包括
        - 环境信息（操作系统，python版本，依赖包版本等）。
        - 我的信息（姓名，年龄，职业，兴趣爱好等）。
        - Tennisbot的基本信息，以及自身的项目结构（可以由她自己生成）
        - 近期会话记录摘要。
        - 有哪些agents，每个是做什么用的。
    此外，Tennisbot运行时应该还要更新一个“近期会话记录摘要”。可以暂时用日记充当。
- logs：运行记录，也要记录聊天文本内容。每天总结此记录，并写入日记。
- tests：本项目的pytest测试代码。
- readme.md：项目的说明文档。
- dev_history.md：开发历史记录。每次更新都要记录在这里，方便回溯

<br>

可以使用matrix（element）当作输入/输出。

如果不行就使用telegram bot。

<br>

先暂时使用着openai agnents sdk，将来可能会迁移到vercel的ai sdk上。

<br>

可以每次加载不同的会话历史记录之类的，使得Tennisbot可以有不同的“心情”/“人格”。

<br>

为了Tennisbot修改方便，各文件可以保持简短。且文件后加一空行。

<br>

tennisbot设计出来是要解决复杂问题的。

就需要多agent并行运行

可以让主agent依据需求，生成一个新agent，有自己独立的工作区

**一个复杂问题对应一个agent**，有重复的任务就让同样的agent来做

新agent也可以不删除，就一直保留着

任何agent都应该有apply diff的能力，只是平时少做

考虑：所有tennisbot共享一个备忘录，里面有要做的事，做的结果。

<br>

（接上）所有tennisbot共享一个备忘录有点太离谱了，可以每个tennisbot在完成一件事时有自己的备忘录文件。中间包括计划，执行过程，结果等。

没想到webui这么复杂。我本以为只是把输出从网页上读下来，然后把输出显示在网页上而已。没想到有框架，而且整个系统逻辑好像也要改。