import os
import json
import importlib

from agents import Agent, ModelSettings
from src.tools import *

def load_agent_tools(tool_names):

    # Import the agents module to access tool classes
    agent_module = importlib.import_module("agents")

    tools = []
    for tool_name in tool_names:
        if tool_name.startswith("openai:"):
            # "openai:WebSearchTool" -> WebSearchTool
            tool = getattr(agent_module, tool_name.split("openai:")[1], None)
            if tool:
                tools.append(tool())
            else:
                print(f"Warning: Tool {tool_name} not found in agents module.")
        else:
            # "read_files"
            # tool = importlib.import_module(f"src.tools.{tool_name}")
            tool = globals().get(tool_name, None)
            if tool:
                tools.append(tool)
            else:
                print(f"Warning: Tool {tool_name} not found in src.tools.")
    return tools

def load_main_agent():
    # Load main agent from agents/main_agent.md

    with open("agents/main_agent.json", "r", encoding="utf-8") as f:
        agent_config = json.load(f)
        model = agent_config.get("model", "gpt-5-mini")
        tools = load_agent_tools(agent_config.get("tools", []))
        temperature = agent_config.get("temperature", 1.0)

    ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open("agents/main_agent.md", "r", encoding="utf-8") as f:
        instructions = f.read().replace("ROOT_PATH", ROOT_PATH)

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

    sub_agents = []
    for dirs in os.listdir("agents/sub_agents"):
        dir_path = os.path.join("agents/sub_agents", dirs)
        if not os.path.isdir(dir_path):
            continue

        agent_file = os.path.join(dir_path, "agent.json")
        if not os.path.exists(agent_file):
            continue
        with open(agent_file, "r", encoding="utf-8") as f:
            agent_config = json.load(f)
            model = agent_config.get("model", "gpt-5-mini")
            tools = load_agent_tools(agent_config.get("tools", []))

            temperature = agent_config.get("temperature", 0.5)
            instructions_original = agent_config.get("instructions", [])
            if isinstance(instructions_original, list):
                instructions = "\n".join(instructions_original)
            else:
                instructions = instructions_original

            sub_agents.append(Agent(
                name=dirs,
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