import os
import sqlite3
import time

from agents import Runner, SQLiteSession

from src.logger import logger
from src.load_agent import create_handoff_obj, load_main_agent, load_sub_agents


def session_cleanup():
    """Cleanup session database files."""
    db_path = "data/session.db"
    if not os.path.exists(db_path):
        logger.log("session.cleanup_skipped db_missing")
        return

    # Reset the session store without deleting files.
    # This keeps the db path stable while returning to an empty state.
    conn = sqlite3.connect(db_path, timeout=0.2)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
        ]
        for table in tables:
            conn.execute(f"DELETE FROM {table};")
    finally:
        conn.close()

    time.sleep(0.1) # otherwise: "cannot VACUUM from within a transaction"

    conn2 = sqlite3.connect(db_path, timeout=0.2)
    try:
        conn2.execute("VACUUM;")
    finally:
        conn2.close()

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

        logger.log("role=user input=" + user_input.replace("\n", "\\n"))

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
        logger.log("role=assistant name=" + name + " output=" + str(result.final_output).replace("\n", "\\n"))

        # TODO：每次会话20分钟后，自动保存会话，并创建新会话
        # TODO: 异步会话，允许同时处理多个用户请求
