import asyncio
import dotenv

from src.run import run_session, session_cleanup
from src.logger import logger


if __name__ == "__main__":

    dotenv.load_dotenv()

    logger.setup()
    logger.log("app.start")

    # TODO: load settings

    # TODO: load schedule tasks

    try:
        # Start session
        asyncio.run(run_session())

    except SystemExit as e:

        # Raised by archive_and_new_session tool
        if e.code == 94:
            # Start a new session
            logger.log("session.archive_and_new_session_requested")
            session_cleanup()
            asyncio.run(run_session())

        # Raised by request_restart tool
        elif e.code == 95:
            logger.log(f"system.exit_requested with code={e.code}")
            session_cleanup()
            raise e
        elif e.code == 96:
            logger.log(f"system.restart_requested with code={e.code}")
            session_cleanup()
            raise e
