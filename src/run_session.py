import os
import sqlite3
import time

from agents import Runner, SQLiteSession, MaxTurnsExceeded

from src.logger import logger
from src.settings import settings


def session_cleanup():
    """Cleanup session database files."""
    db_path = "data/sessions/0.db"
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

async def run_session(agent, session: SQLiteSession):
    """Create agents and session, run the main chat loop."""

    current_agent = agent

    # chat loop, breaks when requied archive session, restart and exit, or error occurs
    while True:

        user_input = input("User: ")

        # Hotkey for archive a session
        if user_input == "=":
            raise SystemExit(94)

        logger.log("chat role=user input=" + user_input.replace("\n", "\\n"))

        try:
            result = await Runner.run(
                current_agent,
                user_input,
                session=session,
                max_turns=settings.default_max_turns,
            )

            last_agent = getattr(result, "last_agent", None)
            if last_agent is not None:
                current_agent = last_agent

            name = getattr(current_agent, "name", "Agent")
            print(f"{name}: {result.final_output}")
            logger.log("chat role=assistant name=" + name + " output=" + str(result.final_output).replace("\n", "\\n"))
            
        except MaxTurnsExceeded:
            logger.log("chat max_turns_exceeded")