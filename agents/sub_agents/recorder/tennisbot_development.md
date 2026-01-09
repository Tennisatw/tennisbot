---
title: Tennisbot 开发记录
abstract: 记录 Tennisbot 的开发过程
prompt: 依据时间顺序，记录 Tennisbot 的开发过程，包括时间线、设计想法、目标与架构等内容。需要时，主动询问用户补充细节。
---

# Tennisbot 开发记录

## 开发前提 / 设计想法（摘自 z/dev_thoughts.md）
- 尽量自举：尽量使用自己/Tennisbot自己开发，尽量不依赖外部现成方案。
- 目标项目结构设想：
  - `start.bat`：启动脚本，依据返回值决定结束/更新并重启。
  - `main.py`：启动入口。
  - `src/`：核心代码
    - `agent.py`：主 agent 实现
    - `settings.json`：设置（供 Tennisbot 自读）
    - `tools/`：工具集合（每个工具单文件）
    - `agents/`：副 agent（developer / browser / computer / 知识库等设想）
    - `AGENT.md`：短小精悍的自述/环境/结构/近期摘要/agents 说明
  - `logs/`：运行记录（含聊天文本），每天总结写入日记（早期用日记充当“近期摘要”）。
  - `tests/`：pytest 测试
  - `readme.md`：说明
  - `dev_history.md`：开发历史记录（便于回溯）
- 多 agent 思路：复杂问题 → 拆成多个 agent 并行；“一个复杂问题对应一个 agent”；可长期保留 agent。
- 记录/备忘录：曾考虑所有 tennisbot 共享备忘录，后觉得过于离谱，倾向于“每个任务/agent 有自己的备忘录文件（计划-执行-结果）”。
- 交互设想：可考虑 Matrix(Element) 或 Telegram bot 作为 I/O。
- 技术路线：先用 OpenAI Agents SDK，将来可能迁移到 Vercel AI SDK。
- 工程习惯：文件保持简短，末尾留空行。
- 经验/吐槽：WebUI 比预想复杂；`draft_patch` 规则太严/可能有引号 bug，倾向更简单的“文件名：替换前/替换后”规则；也认为 Tennisbot 可以更放开地自己写代码。

## 时间线（来自 z/dev_history.md，按时间顺序整理）
### 2025.12.15
- 创建仓库，新建初始文件。
- 安装并使用 uv：
  - `uv init`
  - `uv add openai-agents`
  - 激活 venv：`.\.venv\Scripts\activate`

### 2025.12.16
- 增加依赖：`uv add python-dotenv`

### 2025.12.20
- 为了以后支持更久，计划切换到 Python 3.13。
- 删除并重建环境相关文件：`.venv`、`.python-version`、`pyproject.toml`、`uv.lock`。
- 重新初始化：
  - `uv python install 3.13`
  - `uv init` / `uv venv` / 激活 venv
  - `uv add openai-agents`、`uv add python-dotenv`、`uv add pytest`
- 完善架构构想（见上方“开发前提/设计想法”）。
- 创建 developer agent 草稿。

### 2025.12.28
- 编写 `AGENT.md`，作为 Tennisbot prompt 基础。
- 完善 `main.py`、`src/agent.py` 基础架构：可以启动 Tennisbot 并对话。

### 2025.12.29
- 添加联网搜索功能。
- 编写 tools：`read_file`、`list_files`、`grep`、`apply_patch`。
- 完善 developer sub-agent：Tennisbot 可以通过 developer sub-agent 修改自己的代码。
- 新增 `write_file` 工具：作为补丁失败时的兜底。

### 2025.12.30
- 修改 patch 逻辑：旧 `apply_patch` 失败率高 → 拆成 `draft_patch`（生成 git-style patch）与新的 `apply_patch`（应用 patch）。
- 放松 `git apply --check` 检查：`--recount`、`--ignore-whitespace`。
- 增加依赖：`uv add pytest-asyncio`。
- 新增一些 tool 测试。
- 继续完善 developer sub-agent。
- 完善 `start.bat`：可依据返回值决定是否重启。
- 新增 Tennisbot, the recorder。
- 编写 `src/logger.py`。
- 整理 handoff 逻辑，并用 `handoff` 函数自定义交接。

### 2025.12.31
- 新增调试/运维 tools：
  - `run_python`（运行任意 Python 代码调试）
  - `run_shell`（运行 shell 命令调试）
  - `request_restart`（请求重启/退出）
  - `archive_session`（归档会话并新建会话）
  - `edit_text_file`（仅编辑文本文件，与 `write_file` 区分）
- 完善 `run_session.py`、`main.py`。
- 修改 `draft_patch`：成功率应更高。

### 2026.01.01
- 完善 `session_cleanup`（仍有问题，先将就）。
- 禁用 `archive_session` 工具：改为只能通过热键归档（因为 Tennisbot 经常误用）。
- 开发 WebUI；安装 Node.js。
- 增加依赖：`uv add fastapi uvicorn`、`uv add "uvicorn[standard]"`。
- 安装 pnpm：`npm i -g pnpm`；前端：`cd ./web/frontend/` → `pnpm install`。
- WebUI 基本完成，但存在 bug：`http://10.0.0.31:5173/` 无法发送消息（待修）。
- CLI 仍保留，但逐渐弃用。

### 2026.01.02-03
- WebUI debug。
- 升级为 multi-session。
- 弃用部分 tools：`run_python`。

### 2026.01.04
- 支持多 session 会话，但仍有一些 bug。

### 2026.01.05
- 新增 `edit_apply` 工具。
- 弃用 `draft_patch` 与 `apply_patch`（失败率高）。

## 目标与早期架构（补充自 Tennisatw 口述，2026.01.06 记录）
- 一句话目标：**成为 Tennisatw 的助手，真正帮他解决复杂问题**。
- 框架选型：
  - 曾在 Claude Agent SDK、Vercel AI SDK 等框架之间纠结，甚至考虑自写框架。
  - 最终选择 OpenAI Agents SDK 的原因：
    - 与需求匹配度高
    - **支持 Python**（关键）
    - **支持切换非 OpenAI 模型**（关键）

### 最早期的目录结构构思（早期版本，偏“tools/skills”分层）
- `start.bat`：启动脚本，依据返回值决定结束/更新并重启。
- `main.py`：启动文件。
- `src/`：核心代码（最基础功能）
  - `agent.py`：agent 实现
  - `settings.py`：硬性参数（temperature、top_p 等）
  - `tools.py`：工具集（简单常用功能函数）
- `skills/`：技能（比“工具”更高级一层），每个技能一个文件夹
  - `skills.md`：技能说明（功能/用法/参数；加载技能时先读）
  - `others.py`：该技能可能用到的代码
  - 设想的 skills：
    - 开发自身
    - 维护日记（读取/修改；记录每天大事小事琐事）
    - 生成 Excel
    - 生成 PDF
    - 通过 MCP 操控 Chrome 做自动化
    - 通过 MCP 操控电脑
    - （非核心）文章知识库创建与查询
- `logs/`：运行记录（含聊天文本）；每天总结写入日记。
- `tests/`：整体测试用例；大更新后应运行。
- `readme.md`：说明文档。
- `agent.md`：供 Tennisbot 自读的短文档
  - Tennisatw 基本信息（具体字段待进一步确定）
  - Tennisbot 基本信息 + 项目结构
  - skills 列表与用途
  - 运行时需要更新“近期会话记录摘要”（早期可用日记充当）
- `dev_history.md`：开发历史记录（便于回溯）。

### 2025.12.15-2025.12.20（补充：早期节奏与侧重点）
- 这段时间开发投入不多：主要在**查资料、做框架选型/确定基本架构、把环境搭起来**。
- 早期使用 Python 3.12（后续 2025.12.20 才决定切到 3.13；Tennisatw 表示版本细节本身不关键）。
- 2025.12.15 当天创建的“初始文件”清单已记不清；对当时而言也不是重点，重点是先把项目跑起来与验证方向。

### 2025.12.28（开始大规模开发；跑通最小闭环）
- Tennisatw 从这天开始才有时间进行**大规模开发**。
- 跑通的最小运行闭环：
  - **CLI 输入一句话 → 模型回复 → 打印输出**
  - 已接入 system prompt（通过 `AGENT.md`）
  - 但当时 **还不能使用 tool**（仅对话能力）
- `AGENT.md`（早期版本）与现在整体结构相近，但当时是“三合一”：
  - 将 **main agent / developer / recorder** 的提示词合并在同一个 `AGENT.md` 里（后续才逐步拆分/模块化）。

### 2025.12.29（联网搜索 + developer 工作流雏形；tools 体系成型）
- 对“最小闭环”的定位：Tennisatw 认为一问一答离“真正的助手”还很远；但从项目一开始，对 Tennisbot **应具备的能力清单**基本有把握。
- 联网搜索：属于设想中“必做能力”，并非临时被某个问题卡住才加；当时的不确定点更多在于**工作流程/形态**（如何让她真正像助手一样工作），而不是功能方向。
- developer 能力目标：希望 developer 像 Claude Code 一样——**输入一句话就能直接修改代码**。
- 为支撑“自然语言改代码”的闭环，12.29 认为必须具备的基础 tools：
  - `read_file` / `list_files` / `grep` / `apply_patch`
- 实现顺序与依赖关系：**read → list → grep → apply**。
- 同期把 tools 的“格式/规范”定了下来（作为后续扩展的基础）。

### 补充：自举原则与“developer 优先”
- 从项目最开始，Tennisatw 就计划让 **Tennisbot 自己开发自己**；因此第一个重点建设的副 agent 是 **developer**。
- 早期闭环的形成方式：
  - Tennisatw 手写一部分代码 + 结合“上一代 Tennisbot”的一些代码建议，先把最初版本跑起来。
  - 12.29 那批基础 tools（`read_file/list_files/grep/apply_patch`）的实现方式较“手工”：由 developer 口述代码，Tennisatw 复制粘贴落地。
- 关键拐点：当 developer 具备修改 Tennisbot 代码的能力后，Tennisatw 基本不再使用其他来源的代码；后续代码主要由 developer 生成（直到今天仍然如此）。
- 现状评价：整体仍偏粗糙，但功能已够用。

### 2025.12.30（patch 机制问题暴露与原因分析）
- 旧 `apply_patch` 失败率极高：约 10 个 patch 里 8 个无法通过。
- 主要原因：`git apply` 的校验过于严格，常见卡点包括：
  - 行尾换行（EOL）
  - patch 中的 `a/` `b/` 路径前缀
  - `index` 等元信息
- 更核心的判断：**patch 格式本身复杂，理应由工具自动生成**，而不是让 Tennisbot 手写；让模型直接“写出正确 patch”天然不稳定。

### 代码改动工具链：第一大难关（补充：Tennisatw 的反思与最终路线）
- 核心感悟：即使 Tennisbot 很聪明，也很难“一口气”生成**绝对正确**的 patch；patch 体系里细碎且复杂的约束点太多，导致成功率不稳定。
- “实现代码改动”的 tools 是本项目的**第一个大难关**，并经历了多轮迭代：
  - 2025.12.29：最初打算走 `draft_patch` 路线。
  - 2025.12.30：因成功率过低，将 patch 流程拆成两个工具（生成/应用），并给 developer 准备了多个示例以提高稳定性。
  - 随后：即便如此成功率仍偏低 → 进一步放松 `git apply --check`（如 `--recount`、`--ignore-whitespace` 等）。
  - 2026.01.05：仍然不够稳定 → **彻底放弃 patch**，改用 `edit_apply`：约定一套“基于锚点的文本修改方法”，再由工具按规则执行。
- 对 developer 的评价变化：
  - developer 的开发水平被认为“挺高”，且不太会改错内容。
  - 与“上一代”（如 gpt-4o）对比：上一代生成的修改通常需要 Tennisatw 严格把关；而 developer 相对更省心。
- 工作方式（反复出现的模式）：
  - Tennisatw 提出问题/需求 → 询问 Tennisbot 的实现方案 → Tennisatw 选择一个方案 → 由 Tennisbot 实现开发。

### 2025.12.30（recorder/logger 的动机与演化；补充自 Tennisatw 口述）
- recorder（本 agent）属于“从一开始就想加”的模块。
- recorder 的最初设想并不叫 recorder，而叫 **interrogator**，并聚焦两个功能：
  1) **晚间固定时间聊天**：通过对话把当天发生的事讲清楚；由 interrogator 负责整理——包括你们对话记录的总结 + Tennisatw 的日记（因为 Tennisatw 有记日记习惯，但手打字打烦了）。
  2) **生成一份人格报告**：系统性整理 Tennisatw 的过往经历、性格、世界观等（更像长期“审讯/画像”）。
- 后续演化：随着“需要记录的事情”变多，interrogator 改名为 **recorder**，职责也从上述两项扩展为：**记录任何大大小小的事情**（更通用的记录/归档角色）。
- 实际使用节奏：虽然 12.30 已加入 recorder，但 2025.12.30-2026.01.05 期间主要精力在 WebUI 与 multi-session（两者都关键且系统常处在“接近崩溃/不稳定”的状态），因此当时并没有太多机会真正使用 recorder 进行日常对话记录。

- logger：属于“上一代 Tennisbot”已存在且被验证有用的模块；主要价值是**定位 bug / 追踪问题发生位置**，因此在这一代继续沿用。
- 记录体系的早期设想与现状：
  - 最初设想：程序运行 + 你我输入输出 → 全部进入 logger；然后每天基于 logger 总结生成日记。
  - 现状：logger 与“日记/总结”实现被拆开（分离关注点），但“日记最终应该怎么处理”仍未完全定型。

- 版本备注：按 Tennisatw 的版本序列，上一版约为第六版，本项目为第七版（重要性较低，仅作背景信息）。

### 2025.12.30（handoff / 测试 / start.bat；补充）
- handoff：Tennisatw 认为这是 OpenAI Agents SDK 的一个“很强”的能力。
  - 背景：此前一直不太确定“不同 Tennisbot/不同 agent 之间如何交接”才自然。
  - 12.30：基于 OpenAI Agents SDK 的 handoff 能力，实现了多 agent 的交接逻辑。
  - 行为变化：
    - 之前：每句话默认从 main 开始 → 临时交接给 sub-agent 干活 → 再回到 main。
    - 之后：一旦交接到 sub-agent，会话可**保持在 sub-agent** 侧，持续对话、持续干活（更像真正的工作台/分工）。
  - 稳定性：交接过程基本没出什么乱子。

- 测试：当天写了一些 pytest，用于测试不同的 tool。

- `start.bat`（后更名 `start_cli.bat`）：
  - 机制：当 Tennisbot 请求重启/关闭时，通过返回不同的退出码来决定“重启/关闭”。
  - 动机：这是从上一版就想实现的能力，用于形成开发闭环：**developer 修改代码 → 重启 → 应用新代码**，相当于“不停机更新”。
  - 后续变化：转向 WebUI 后，Tennisbot 的运行主逻辑发生了较大变化；`start.bat` 因此更名为 `start_cli.bat`（CLI 仍保留，但不再是唯一主入口）。
  - 备注：WebUI 的体量与复杂度超出最初预期（此前没有开发 WebUI 的经验，也没预设它会变得这么大）。

### 2025.12.31（调试/运维 tools：自举、自控与记录能力；补充）
- `run_shell` / `run_python`：属于从上一代继承的工具。
  - 目的：让 Tennisbot 具备一定的**自举能力**，以及更强的“自我控制 / 自我认知”能力（能自己跑命令、自己验证假设、自己调试）。
- `request_restart`：用于让 main agent 控制程序退出码，从而实现**自我控制**——决定是重启还是关机（配合 `start.bat/start_cli.bat` 的重启策略）。
- `archive_session`：当时并未真正实现完整的“归档”，更接近于**删除旧对话记录**（清理历史），属于早期占位/雏形。
- `edit_text_file`：被认为是“更新目的非常明确”的工具。
  - 动机：recorder 需要稳定维护记录，不可能用 `draft_patch` 来写日志。
  - 设计取舍：
    - 相比 `write_file`，`edit_text_file` 默认 append，更符合日志/记录的写入方式。
    - 且它只允许编辑文本文件，风险更可控。
    - 因此没有对 recorder 放开 `write_file` 权限。

### 2026.01.01（WebUI：多设备使用的动机；技术栈敲定；运行逻辑被迫重构）
- 关键认知变化：Tennisatw 起初**没预料到 WebUI 会直接影响 Tennisbot 的运行主逻辑**；原因是此前没有前后端开发经验，对“前端/后端/启动方式/会话管理”这套复杂度估计不足。
- 启动脚本分化：
  - `start_cli.bat`：仅用于 CLI 启动（作为备份通道）。
  - 新增 `start_webui.bat`：用于启动 WebUI 前端/后端。
- WebUI 的主要动机：
  - **多设备同时使用** Tennisbot
  - 更贴近生活的使用场景：例如半夜躺在被窝里也能聊天
  - UI 更好看、更顺手
- 技术栈决策：与 developer 讨论很久后敲定：**Svelte 5 + Vite 6 + TailwindCSS + FastAPI**。
- 对 developer 的感受：Tennisatw 认为 developer 水平很高，框架几乎没怎么折腾就搭起来了；也不排除“其实框架本身不难，只是自己不熟”。
- 开发协作习惯：每当环境/框架/文件组织约定更新，Tennisatw 会同步更新到 developer 的 agent 信息中，让 developer 能“上来就知道该看哪些文件”，减少反复询问与定位成本。
- `archive_session` 的弃用原因：可能是“名字起得不好”导致主 agent 产生概念混乱。
  - 现象：main Tennisbot 出现误用/误判，例如误以为交接前要先归档、混淆“归档 vs 重启”等。
  - 处理：弃用 `archive_session`；改为在 WebUI 点击 `end session` 后**自动归档**（把归档动作绑定到明确的 UI 行为）。

### 2026.01.01（WebUI 大 bug：页面发不了消息；定位过程）
- bug 描述：WebUI 页面无法发送消息。
- 排查过程：developer 一度也没搞明白，曾误以为是手机端问题，排查许久未果。
- 最终发现：问题与 `10.0.0.31` 相关；本质并不算大问题，打开浏览器控制台输出即可看出线索。
- CLI 的定位：转向 WebUI 后，CLI 主要作为**备份**，用于防止 WebUI 突然连不上。

### 反思：自举的“同时性悖论”
- 事后回看，Tennisatw 认为一个很蠢但真实的问题是：
  - 系统可以“自己开发自己”，但很难“当场、同时”开发自己。
  - 一旦改出严重 bug 导致系统无法对话，就没法继续让 developer 修复，甚至连回滚都困难。
- 暂时解决方案：使用 GitHub 做备份；出现严重 bug 时通过回滚恢复。

## 2026.01.02（WebUI：runtime events 推送到前端；渲染 meta 行）
- 目标：通过 WebSocket 把 server-side runtime events（tool calls / agent handoffs）实时推送到 WebUI；同时优化聊天渲染与排版。

### 后端（src/logger.py / web/backend/app.py）
- `src/logger.py`
  - 强化 `@logged_tool`：在 tool 执行前/后/报错时发结构化事件：`tool_call` + `phase(start/end/error)`，并带 `elapsed_ms` / `error` 等信息。
  - 新增 `Logger.emit(payload)`：作为结构化事件出口（默认仍可单行日志）。
- `web/backend/app.py`
  - 新增 in-process `EventBus`（async queue + broadcast loop），向所有 WS client 广播事件。
  - 将 `logger.emit` 接到 `event_bus.publish`：tool/agent 事件可直接推到 WebUI。
  - WS connect/disconnect 时注册/注销 client。

### 前端（web/frontend/src/App.svelte）
- 新增 `role: 'meta'` 消息类型：
  - `tool_call` 事件渲染为 meta 行（非气泡）。
  - `agent_handoff` 事件渲染为 meta 行（如 `[handoff] -> <agent>`）。
  - meta 行加粗（`font-semibold`）。
- Markdown/排版：
  - markdown 规范化：把 3+ 连续换行压到 2（减少空白）。
  - user 消息也支持 markdown；深色背景下用 `prose-invert` 保证可读性。
  - 字号整体调大；行高用 `leading-snug` 收紧。

### 备注 / follow-ups
- 主题色实验做过但后来被用户回滚。
- 若 Pylance 因 `@dataclass(frozen=True)` 报错（给 `logger.emit` 赋值），可考虑 `object.__setattr__` 或移除 `frozen`。

### 2026.01.02-03（multi-session：对标 ChatGPT；为长任务并行做准备）
- multi-session 也是从项目最开始就想做的能力，目标对标 OpenAI 的 ChatGPT 产品形态。
- 动机：考虑到未来会有很多**长时间任务**，不能让“一个任务卡死”影响其他任务/对话。
- 形态（WebUI 侧）：
  - 同一网页内：左侧栏可选择 session；选中后即在该 session 下对话。
  - 提供 `new session` 与 `end session` 按钮用于创建/结束会话。
- 现状：multi-session 的复杂度高，至今仍有不少 bug 未完全修完；Tennisatw 计划继续集中精力处理。
- `run_python` 的弃用原因：
  - 存在线程不安全风险。
  - 且其能力可被 `run_shell` 覆盖（`run_python` 能做的基本都能用 `run_shell` 完成）。

## 2026.01.04（WebUI：multi-session 模式落地；每个 session 独立 DB）
- 目标：把 Tennisbot 的 WebUI 变成类似 ChatGPT/微信的多会话形态：可创建多个 session、侧边栏切换、一次只展示一个会话。

### 存储方案
- 每个 session 一个 SQLite DB：`data/sessions/<session_id>.db`。
- session 索引：`data/sessions/index.json`。
- `session_id`：用 Unix epoch 毫秒（字符串）。同一毫秒内重复点两次 New session 只创建一个（去重）。
- 启动时以磁盘上的 `data/sessions/*.db` 为准：扫描 DB 文件并重建/修复 `index.json`；尽量保留 `active_session_id`。

### UI/UX（前端）
- 两栏布局：左侧 sidebar 列 session 列表（暂时用 session_id 当名字），右侧复用现有 chat UI。
- sidebar 提供 **New session**：`POST /api/sessions` 创建后自动切换。
- chat 页提供 **End session**（前端占位）：关闭 WS、清空 chat state，右侧显示空白/欢迎页；左侧 sidebar 仍保留，点任意 session 可恢复聊天。
- “No session” 语义：磁盘上没有 DB 文件时，自动创建/加载默认 session。
- 延后项：End session 未来应归档并删除 session DB；暂不在 UI 做 archived 状态。

### 后端 API / 行为（FastAPI）
- `POST /api/sessions`：创建 session，并预热该 session 的 agent bundle（`agents_by_session[session_id] = _new_session_agent()`）。
- `PUT /api/sessions/{session_id}/active`：把 active session 持久化到 `index.json`。
- `GET /api/messages`：支持 `session_id` query param（按 session 拉历史）。

### 2026.01.05：
  - 新增 `edit_apply` 工具，作为 developer 日常改代码的主力工具；上线后代码改动失败率显著下降。

## 2026.01.06（当日补记：工具弃用原因、交互形态调整、当前工作）
  - 修改 recorder 的 `agent.md`
  - 与 recorder 对话，把开发记录系统性补全（避免过几天遗忘）

- 多 agent 规划（仍在考虑）：除常备主 agent 外，倾向于“**一个复杂问题对应一个 agent**”，例如：
  - 更新小红书
  - 管理 shell 任务
  - 写文章
## 2026.01.06
- 调整记录体系：计划将 **session 存储从 db 文件切换为 jsonl**（开发记录新增）。

## 2026.01.06 WebUI multi-session：New session 仍停留在老 session / 消息发到老 session（dev bug 记录）
- 现象：点击 **New session** 后，界面仍停留在老 session；发送消息也会进入老 session。用户反馈：即使等待很久后再发，也仍会触发（非纯竞态）。
- 初步判断：核心是 **WebSocket 切 session 时的“连接归属”不够强约束**。
  - 后端 ws 在握手时用 query param `session_id` 绑定 session；`/api/sessions/{id}/active` 只影响 index 的 active_session_id，不会改变已建立 ws 的 session。
  - 前端缺少“只接受当前 ws 的消息”的硬门禁，旧 ws 回调可能污染新 UI。

### 前端修复（web/frontend/src/App.svelte）
1) **stale socket drop**：`connect(sessionId)` 改为局部 `sock`，并在 `onopen/onclose/onerror/onmessage` 里加 `if (sock !== ws) return;`，避免旧连接消息/事件污染当前 UI。
2) **绑定校验**：新增 `wsSessionId`，在收到后端 `meta/ws_bound` 时记录 socket 实际绑定的 session。
3) **防误发 + 自动补发**：
   - `send()` 中若 `wsSessionId !== activeSessionId`，不直接发送；改为把文本写入 `queuedText`，触发 `connect(activeSessionId)`。
   - 在 `ws_bound` 且 session 匹配后，自动 flush `queuedText` 并发送（用户不再看到 `[warn] socket not bound...`，也不需要点第二次）。
4) **切换 session 顺序优化**（不动 New session）：`switchSession()` 改为先 `connect(sessionId)`，再 best-effort `setActiveSession(sessionId)`，最后 `refreshSessions()`，减少“UI 切了但 ws 还没切”的窗口。
5) **右上角状态三态**：`status` 从两态扩展为 `'disconnected' | 'connected' | 'new session'`；`resetChatState()` 时置为 `'new session'`，等待 `onopen` 再变 `connected`。

### 过程中的小插曲/现象
- 修复后出现提示：`[warn] socket not bound to active session, reconnecting...`。
  - 解释：activeSessionId 已更新，但 ws 尚未收到 `ws_bound`（wsSessionId 仍为 null）或 ws_bound 偶发丢失/未处理。
  - 处理：引入 queuedText + ws_bound 后自动补发，消除 warn 并提升体验。

- 用户观察：New session 后右上角一直显示 disconnected，直到发出一条消息才变 connected。
  - 处理思路：不引入 connecting（用户要求中间态命名为 `new session`），通过 resetChatState 设置该状态改善“状态显示不及时”。

结论：无需从 0 重构，属于“少量关键不变式（invariants）没收口”导致的串台；通过前端 ws 生命周期强约束 + 绑定校验即可稳定修复。

## 2026.01.07（WebUI pending/thinking 精确追踪 + edit_apply 工具安全护栏）

### WebUI：右上角 thinking 状态修复（web/frontend/src/App.svelte）
- 问题：右上角一直显示 `connected`，即使模型在思考。
- 原因：`pendingMessageIds` 没有在发送/queued flush 时 `add`，且 `assistant_message` 分支未按 `in_reply_to/parent_id` 清除 pending。
- 修复：
  - `send()`：发送前 `pendingMessageIds.add(id)`。
  - `meta/ws_bound` 的 queuedText flush：补发前 `pendingMessageIds.add(id)`。
  - `assistant_message`：读取 `msg.in_reply_to`（fallback `msg.parent_id`）命中则 `pendingMessageIds.delete(replyTo)`。
  - UI 仍用 `{#if pendingMessageIds.size > 0} thinking... {:else} {status} {/if}`。

### WebUI：后端协议补充 in_reply_to（web/backend/app.py）
- `assistant_message` payload 新增：`"in_reply_to": message_id`（指向触发该回复的 user_message id），用于前端精确清 pending。
- 保留原字段：`message_id`（assistant uuid）、`parent_id`（仍为 user message id）。

### 工具：edit_apply 安全性改进（src/tools/edit_apply.py）
- 新增硬护栏：**anchor 必须唯一**，否则拒绝修改并返回 `Anchor not unique (hits=...)`。
- 因 anchor 唯一，移除 `occurrence` 机制：
  - `Instruction` schema / docstring 删除 `occurrence`。
  - 删除 `_find_nth()` 与 occurrence 校验逻辑。
  - anchor 定位改为 `text.find(anchor)`。
  - 错误文案微调：`Failed to locate anchor occurrence` → `Failed to locate anchor`。
- 动机：避免“anchor 不唯一 + 宽正则 match”导致跨块误伤（此前曾把 `App.svelte` 结构替换坏）。

## 2026.01.07（补记：web/backend/app.py 的 EventBus/WS 简化改造 + edit_apply 使用经验）
- 目标：
  - 合并两套推送通道（WS 直发 vs EventBus），只保留 EventBus。
  - 简化 EventBus 数据结构与过滤逻辑。

### 后端改动（web/backend/app.py）
- EventBus：
  - `_clients: set + _session_by_client` 合并为 `dict[WebSocket, str|None]`。
  - `run()` 中一次性 snapshot `list(self._clients.items())`，减少锁粒度。
  - session 过滤：payload 带 `session_id` 时按字符串相等过滤。
- WS：
  - 新增 `_ws_publish(session_id, payload)`，统一 WS outbound 走 EventBus，并自动补 `session_id`。
  - `ws_bound / ack / error / assistant_message` 等消息逐步改为 `_ws_publish`。
  - 多次小 patch 导致缩进漂移，最后通过“整段重排 ws_endpoint”恢复为可运行版本。
  - 将 ws_endpoint 中的 `print(...)` 统一替换为 `logger.log(...)`（ws.recv / ws.runner.start/done/error / ws.sent）。
- 注释补充：为模块、EventBus、_ws_publish、ws_endpoint、run_lock、last_agent 等补了简短注释；过程中因插入点/换行不严谨导致缩进与语法被破坏，随后修复。

### edit_apply 工具使用反思（经验总结）
- 常见错误：
  - `Match not found after anchor`：match 是严格字面匹配，缩进/换行/引号/转义差一点就失败。
  - `Anchor not unique (hits=N)`：anchor 选得太泛（如 `print(`、`except Exception:`）会命中多处。
  - “改成功但缩进坏了”：工具不理解 AST，content 缺少换行或缩进不对会直接拼坏代码。
- 注意事项：
  - 优先“小刀法”（只改一行/一个分支），必要时再“整段重排”（尤其函数缩进漂移时）。
  - anchor 选唯一且稳定的行（常量/函数签名/独特字面量），避免高频关键字。
  - match 尽量短，并从 read_file 直接复制源片段，减少手打差异。
  - 插入注释/控制流（try/except/with/if）附近尤其要检查换行与缩进，否则容易 SyntaxError。

## 2026.01.08（WebUI：Streaming 输出协议与落地要点备忘）
- 目标：WebUI 支持 assistant 边生成边显示：后端通过 WS 推 `assistant_text_delta`，结束时再推 `assistant_message_final` 收口气泡。

### 前端现状（web/frontend/src/App.svelte）
- 已支持：
  - `assistant_text_delta`：按 `reply_to`（user message_id）找到对应 assistant 气泡并 append；不存在就新建。
  - `assistant_message_final`：按 `reply_to` 将气泡文本替换为最终 text；不存在就新建。
- 也已支持：`meta/ws_bound`、`ack`、`transcript_final`、`tool_call`、`agent_handoff`、`error` 等。

### 后端落地方向（web/backend/app.py）
- 需要把 `Runner.run(...)` 切到 Agents SDK 的 streaming API：
  - 流式过程中对每个 `ResponseTextDeltaEvent` 发：`{type:"assistant_text_delta", reply_to, delta}`。
  - 流结束后发：`{type:"assistant_message_final", message_id, reply_to, text}`（final text 以 SDK `final_output` 为准，避免与 delta 拼接不一致）。
  - 同步 `agents_by_session[session_id] = result.last_agent`。
- 同一套流程应用于：普通 `user_message` 以及 voice_input → transcript_final 之后的 agent 回复。

### 注意事项 / 坑
- 仍需 per-session lock，避免并发 run 导致 session 状态互相污染。
- delta 必须带正确的 session 作用域（当前 EventBus 可按 `session_id` 过滤）。
- 可选：WS 断开时 best-effort 取消流（非硬性）。
- 验收点：长回复应能看到 token-by-token 增长；切 session 不串台；tool/handoff meta 仍可显示。

## 2026.01.08（WebUI：Voice Mode 规划；STT 已落地，TTS 分段播放待实现）
- 总目标：WebUI 增加语音输入 + 语音输出（分段 TTS 播放），并且与文本聊天共用同一 session/历史/UI 线程。
- 里程碑：
  - Phase 1：voice input + 基于最终回复文本的分段 TTS（非文本流）。
  - Phase 2：assistant delta text → delta 驱动分段 TTS（唯一计划中的 Phase 2 增量）。

### 已实现（STT）
- 协议：Client `voice_input {session_id, message_id, audio_b64, mime}`；Server 回 `transcript_final {session_id, message_id, text}`，并继续走现有 `assistant_message` 文本输出。
- 后端（web/backend/app.py）：
  - `VOICE_INPUT_MAX_BYTES = 20MB`；base64 严格校验 + 大小限制。
  - ffmpeg 转码为 `wav 16k mono pcm_s16le`（临时目录）。
  - faster-whisper：`VOICE_STT_MODEL_SIZE = "medium"`，GPU `cuda/float16`；全局单例模型 + lock 防并发加载。
  - 转码与转写都放到 `asyncio.to_thread(...)`，避免阻塞 event loop。
  - transcript_final 回传后，用转写文本驱动 agent 执行并回 assistant_message。
- 前端（web/frontend/src/App.svelte）：
  - 输入框旁 Voice toggle：录音中显示 Stop。
  - MediaRecorder 录音；停止后插入 placeholder 用户消息 `(transcribing...)`（id=message_id），发 voice_input。
  - 收到 transcript_final 后按 message_id 精准替换 placeholder。
  - 处理切 session race：用 `meta/ws_bound` + `wsSessionId`；未 bound 时把 payload 暂存到 `queuedVoicePayload`，bound 后再 flush。

### 语音输出（TTS）
- 分段规则：以 `。！？\n` 作为切分点，`min_chars_per_chunk = 16`；短句不足 16 则继续缓冲并与后续句子合并。
- 反压策略：waterline（最多 5 个 frozen segment）+ `tail_buffer`。
- 协议扩展：
  - Client → Server：`voice_output_toggle {session_id, enabled}`。
  - Server → Client：`tts_audio_segment {session_id, reply_to, seq, text, audio_b64, mime:"audio/mpeg"}`、`tts_done {session_id, reply_to}`。
- 后端架构要点：每 session 一个 TTS worker；串行合成保证顺序；toggle off / disconnect 需要取消并清空队列，不做断线重放。
- 使用 openai的 TTS API

## 2026.01.09（补记：在高强度日程下仍推进开发）
- 上午 11:00-12:00 与 Reza 开会。
- 下午送快递到 21:00，晚上继续开发 Tennisbot。
- 同期个人假期计划被大幅压缩：原本预计将近一个月，实际真正休假约 3-4 天。

## 2026.01.08（补记：时间被现实任务挤占；假期预期落差）
- 原计划 2025.12.15-2026.01.15 基本空出来。
- 实际被送快递、修车等现实事务占用很多；其余空余时间大量投入 Tennisbot 开发。
- 对假期缩水有点小不爽；计划过两天好好休息。
