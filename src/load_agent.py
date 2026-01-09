import os
import json
import importlib
import frontmatter
import random

from agents import Agent, ModelSettings
from agents import handoff
from src.logger import logger
from src.settings import settings
from src.tools import *


def prompt_replace(prompt: str):
    if "<NAME>" in prompt:
        prompt = prompt.replace("<NAME>", settings.name)
    
    if "<DEFAULT_PROMPT>" in prompt:
        default_prompt = "\n".join(settings.default_prompt)
        prompt = prompt.replace("<DEFAULT_PROMPT>", default_prompt)

    if "<ROOT_PATH>" in prompt:
        ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt = prompt.replace("<ROOT_PATH>", ROOT_PATH)

    if "<PREVIOUS_CONV_SUMMARY>" in prompt:
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

            prompt = prompt.replace("<PREVIOUS_CONV_SUMMARY>", summary)
        except Exception:
            prompt = prompt.replace("<PREVIOUS_CONV_SUMMARY>", "")

    if "<CURRENT_MOOD>" in prompt:
        # Valence, Arousal, Stress, Energy
        # 愉快程度，亢奋程度，压力值，精力值
        valence = random.randint(2, 8)
        arousal = random.randint(2, 8)
        stress = random.randint(2, 8)
        energy = random.randint(2, 8)
        mood_str = f"Valence:{valence}, Arousal:{arousal}, Stress:{stress}, Energy:{energy} (out of 10)"
        prompt = prompt.replace("<CURRENT_MOOD>", mood_str)

    if "<DEVELOPER_MD_FILES>" in prompt:
        developer_md_contents = ''
        for file in os.listdir("agents/sub_agents/developer"):
            file_path = os.path.join("agents/sub_agents/developer", file)
            if file.endswith(".md") and file != "agent.md" and not file.startswith("_"):
                post = frontmatter.load(file_path)
                title = post.get("title", file)
                abstract = post.get("abstract", "No Abstract")
                developer_md_contents += f"{title}: {abstract}\n"
        prompt = prompt.replace("<DEVELOPER_MD_FILES>", developer_md_contents)

    if "<RECORDER_MD_FILES>" in prompt:
        recorder_md_contents = ''
        for file in os.listdir("agents/sub_agents/recorder"):
            file_path = os.path.join("agents/sub_agents/recorder", file)
            if file.endswith(".md") and file != "agent.md" and not file.startswith("_"):
                post = frontmatter.load(file_path)
                title = post.get("title", file)
                abstract = post.get("abstract", "No Abstract")
                recorder_md_contents += f"{title}: {abstract}\n"
        prompt = prompt.replace("<RECORDER_MD_FILES>", recorder_md_contents)

    return prompt


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

    with open("agents/agent.md", "r", encoding="utf-8") as f:
        instructions = prompt_replace(f.read())
        print("Loaded main agent: Tennisbot")
        print(instructions)

    # Inject summaries of previous conversations into <PREVIOUS_CONV_SUMMARY>

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
            instructions = prompt_replace(f.read())
            print(f"Loaded sub-agent: Tennisbot the {dirs}")
            print(instructions)

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