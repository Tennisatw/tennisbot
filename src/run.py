from agents import Runner
from src.logger import logger


def _log_chat(role: str, content: str, *, agent_name: str | None = None) -> None:
    """Log full chat content.

    Notes:
        - Keep content untruncated for complete transcripts.
        - Replace newlines to keep one log line per event.
    """

    content = content.replace("\r\n", "\\n").replace("\n", "\\n")
    if agent_name:
        logger.log(f"chat role={role} agent={agent_name} content={content}")
    else:
        logger.log(f"chat role={role} content={content}")

async def run(agent, session):
    
    # Keep the active agent across turns.
    # Handoffs only affect the current Runner.run() call unless we persist it.
    current_agent = agent
    turn = 0

    while True:
        user_input = input("User: ")
        turn += 1
        logger.log(f"chat.turn={turn}")
        _log_chat("user", user_input)

        result = await Runner.run(
            current_agent,
            user_input,
            session=session,
            max_turns=30,
        )

        last_agent = getattr(result, "last_agent", None)
        if last_agent is not None:
            current_agent = last_agent

        name = getattr(current_agent, "name", "Agent")
        print(f"{name}: {result.final_output}")
        _log_chat("assistant", str(result.final_output), agent_name=name)

        # TODO：每次会话15分钟后，自动保存会话，并创建新会话
        # TODO: 异步会话，允许同时处理多个用户请求
