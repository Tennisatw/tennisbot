# CLI 模式的会话运行器

import os
import time

from agents import Runner, MaxTurnsExceeded

from src.jsonl_session import JsonlSession

from src.logger import logger
from src.settings import settings


def session_cleanup(session_path: str = "data/sessions/0.jsonl"):
    """Cleanup session store files."""

    if not os.path.exists(session_path):
        logger.log("session.cleanup_skipped store_missing")
        return

    # Reset the session store without deleting files.
    tmp_path = session_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write("")
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_path, session_path)
    logger.log("session.cleanup_completed")


async def run_session(agent, session: JsonlSession):
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
                session=session, # type: ignore
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