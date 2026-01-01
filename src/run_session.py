import os

from agents import Runner, SQLiteSession

from src.logger import logger
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
    # TODO：使用更优雅的方法清理，而不是直接删除。这样会有bug。
    # db_path = "data/session.db"
    # wal_path = f"{db_path}-wal"
    # shm_path = f"{db_path}-shm"

    # if not os.path.exists(db_path):
    #     logger.log("session.cleanup_skipped db_missing")
    #     return

    # conn = sqlite3.connect(db_path, timeout=0.2)
    # try:
    #     conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    #     conn.execute("VACUUM;")
    # finally:
    #     conn.close()

    # if os.path.exists(wal_path):
    #     os.remove(wal_path)
    # if os.path.exists(shm_path):
    #     os.remove(shm_path)

    # os.remove(db_path)

    logger.log("session.cleanup_completed")

async def run_session():
    """Create agents and session, run the main chat loop."""

    # load agents and handoffs
    agent = load_main_agent()
    agent_handoff_obj = create_handoff_obj(agent)
    agents_list = load_sub_agents(handoffs=[agent_handoff_obj])
    agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in agents_list]

    # Create a session
    os.makedirs("data", exist_ok=True)
    session = SQLiteSession("tennisbot", db_path="data/session.db")

    current_agent = agent

    # chat loop, breaks when session ends
    while True:

        user_input = input("User: ")

        # Hotkey for archive and start a new session
        if user_input == "=":
            raise SystemExit(94)

        _log_chat("user", user_input)

        result = await Runner.run(
            current_agent,
            user_input,
            session=session,
            max_turns=20,
        )

        last_agent = getattr(result, "last_agent", None)
        if last_agent is not None:
            current_agent = last_agent

        name = getattr(current_agent, "name", "Agent")
        print(f"{name}: {result.final_output}")
        _log_chat("assistant", str(result.final_output), agent_name=name)


        # End of session cleanup
        # TODO: 新建agent总结会话，保存到data/session_summaries/yyyy-mm-dd_hh-mm-ss.md

        # TODO：每次会话20分钟后，自动保存会话，并创建新会话
        # TODO: 异步会话，允许同时处理多个用户请求
