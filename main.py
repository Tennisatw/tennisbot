import os
import asyncio
import dotenv

from agents import SQLiteSession
from src.load_agent import create_handoff_obj, load_main_agent, load_sub_agents
from src.run_session import run_session, session_cleanup
from src.logger import logger


if __name__ == "__main__":

    dotenv.load_dotenv()

    logger.setup()
    logger.log("app.start")

    # TODO: load settings

    # TODO: load schedule tasks

    # TODO: load GUI

    while True:
        try:
            # load agents and handoffs
            agent = load_main_agent()
            agent_handoff_obj = create_handoff_obj(agent)
            agents_list = load_sub_agents(handoffs=[agent_handoff_obj])
            agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in agents_list]

            # Create a session
            os.makedirs("data", exist_ok=True)
            session = SQLiteSession("tennisbot", db_path="data/session.db")

            # Start session
            asyncio.run(run_session(agent, session))

        except SystemExit as e:

            # Raised by archive_session tool
            if e.code == 94: # Start a new session
                logger.log("app.start_new_session")
                session_cleanup()

            # Raised by request_restart tool
            elif e.code == 95: # Exit application
                logger.log(f"app.exit")
                raise e
            elif e.code == 96: # Restart application
                logger.log(f"app.restart")
                raise e

    # TODO: 允许多开session