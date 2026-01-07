import os
import json
import importlib

from agents import Agent, ModelSettings
from agents import handoff
from src.logger import logger
from src.tools import *


# class LoggedOpenaiTool:
#     """A thin wrapper to log every openai tool call."""

#     def __init__(self, inner):
#         self._inner = inner

#     @property
#     def name(self) -> str:
#         return getattr(self._inner, "name", self._inner.__class__.__name__)

#     def __getattr__(self, item):
#         return getattr(self._inner, item)

#     async def __call__(self, *args, **kwargs):
#         logger.log(f"tool.call {self.name} args={args} kwargs={kwargs}")
#         res = self._inner(*args, **kwargs)
#         if inspect.isawaitable(res):
#             return await res
#         return res

def load_agent_tools(tool_names):

    # Import the agents module to access tool classes
    agent_module = importlib.import_module("agents")

    tools = []
    for tool_name in tool_names:
        if tool_name.startswith("openai:"):
            # "openai:WebSearchTool" -> WebSearchTool
            short_name = tool_name.split("openai:")[1]
            tool = getattr(agent_module, short_name, None)
            if tool:
                # inst = LoggedOpenaiTool(tool())
                tools.append(tool())
            else:
                logger.log(f"Warning! tool_not_found_in_agents_module tool={tool_name}")
        else:
            # "read_files"
            tool = globals().get(tool_name, None)
            if tool:
                tools.append(tool)
            else:
                logger.log(f"Warning! tool_not_found_in_src_tools tool={tool_name}")
    return tools

def load_main_agent():
    # Load main agent from agents/agent.md

    with open("agents/agent.json", "r", encoding="utf-8") as f:
        agent_config = json.load(f)
        model = agent_config.get("model", "gpt-5-mini")
        tools = load_agent_tools(agent_config.get("tools", []))
        temperature = agent_config.get("temperature", 1.0)

    ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open("agents/agent.md", "r", encoding="utf-8") as f:
        instructions = f.read().replace("<ROOT_PATH>", ROOT_PATH)

    # Inject summaries of previous conversations into <PREVIOUS_CONV_SUMMARY>
    summary = ""
    n_summaries = 10
    try:
        files = sorted(os.listdir("data/session_summaries"), reverse=True)
        for index, f in enumerate(files):
            if index >= n_summaries:
                break
            summary_file = os.path.join("data/session_summaries", f)
            with open(summary_file, "r", encoding="utf-8") as sf:
                prev_summary = sf.read()
                summary = prev_summary + "\n" + summary

        instructions = instructions.replace("<PREVIOUS_CONV_SUMMARY>", summary)
    except Exception:
        instructions = instructions.replace("<PREVIOUS_CONV_SUMMARY>", "")

    agent = Agent(
        name="Tennisbot",
        instructions=instructions,
        model=model,
        tools=tools,
        model_settings=ModelSettings(
            temperature=temperature,
            max_tokens=2048,
        ),
    )
    return agent


def load_sub_agents(handoffs):
    # Dynamically load sub-agents from agents/sub_agents/

    ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    sub_agents = []
    for dirs in os.listdir("agents/sub_agents"):
        dir_path = os.path.join("agents/sub_agents", dirs)
        if not os.path.isdir(dir_path):
            continue
        if dirs.startswith('_'):
            continue

        agent_file = os.path.join(dir_path, "agent.json")
        if not os.path.exists(agent_file):
            continue
        with open(agent_file, "r", encoding="utf-8") as f:
            agent_config = json.load(f)
            model = agent_config.get("model", "gpt-5-mini")
            tools = load_agent_tools(agent_config.get("tools", []))

            temperature = agent_config.get("temperature", 0.5)
        with open(os.path.join(dir_path, "agent.md"), "r", encoding="utf-8") as f:
            instructions = f.read().replace("<ROOT_PATH>", ROOT_PATH)

            sub_agents.append(Agent(
                name="Tennisbot the " + dirs,
                instructions=instructions,
                model=model,
                tools=tools,
                model_settings=ModelSettings(
                    temperature=temperature,
                    max_tokens=2048,
                ),
                handoffs=handoffs,
            ))

    return sub_agents

def create_handoff_obj(agent):
    if agent.name == "Tennisbot":
        with open("agents/agent.json", "r", encoding="utf-8") as f:
            agent_config = json.load(f)
            tool_description = agent_config.get("handoff_description", "")
    else:
        folder_name = agent.name.replace("Tennisbot the ", "")
        with open(f"agents/sub_agents/{folder_name}/agent.json", "r", encoding="utf-8") as f:
            agent_config = json.load(f)
            tool_description = agent_config.get("handoff_description", "")

    async def on_handoff(_):
        logger.log(f"agent.handoff to {agent.name}")
        await logger.emit({"type": "agent_handoff", "to_agent": agent.name})

    handoff_obj = handoff(
        agent=agent,
        on_handoff=on_handoff,
        tool_description_override=tool_description
    )

    return handoff_obj