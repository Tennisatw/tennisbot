import os

from agents import Runner, SQLiteSession

from src.logger import logger
from src.globals import SessionRolloverError
from src.load_agent import create_handoff_obj, load_main_agent, load_sub_agents


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


def session_cleanup():
    """Cleanup session database files."""
    # TODO: 尝试用更优雅的方法清理SQLite数据库文件
    db_paths = [
        "data/session.db",
        "data/session.db-wal",
        "data/session.db-shm",
    ]

    for p in db_paths:
        if os.path.exists(p):
            os.remove(p)
    
    logger.log("session.cleanup_completed")

async def run():

    # main event loop
    while True:

        # load agents and handoffs
        agent = load_main_agent()
        agent_handoff_obj = create_handoff_obj(agent)
        agents_list = load_sub_agents(handoffs=[agent_handoff_obj])
        agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in agents_list]

        # Create a session
        os.makedirs("data", exist_ok=True)
        session = SQLiteSession("tennisbot", db_path="data/session.db")
    
        current_agent = agent

        # chat loop, breaks when session ends (SessionRolloverError raised)
        try:
            while True:

                user_input = input("User: ")

                # Hotkey for session rollover
                if user_input == "=":
                    raise SessionRolloverError()

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

        except SessionRolloverError:
            # Raised by timeout, "=" hotkey and rollover_session tool
            logger.log("session.rollover_requested")
            session_cleanup()
        
        except SystemExit as e:
            # Raised by request_restart tool
            logger.log(f"system.exit_requested with code={e.code}")
            session_cleanup()
            raise e

        # End of session cleanup
        # TODO: 新建agent总结会话，保存到data/session_summaries/yyyy-mm-dd_hh-mm-ss.md

        # TODO：每次会话20分钟后，自动保存会话，并创建新会话
        # TODO: 异步会话，允许同时处理多个用户请求
