import asyncio
import dotenv

from src.run_session import run_session, session_cleanup
from src.logger import logger


if __name__ == "__main__":

    dotenv.load_dotenv()

    logger.setup()
    logger.log("app.start")

    # TODO: load settings

    # TODO: load schedule tasks

    while True:
        try:
            # Start session
            asyncio.run(run_session())

        except SystemExit as e:

            # Raised by archive_and_new_session tool
            if e.code == 94: # Start a new session
                logger.log("app.start_new_session")
                session_cleanup()

            # Raised by request_restart tool
            elif e.code == 95: # Exit application
                logger.log(f"app.exit")
                session_cleanup()
                raise e
            elif e.code == 96: # Restart application
                logger.log(f"app.restart")
                session_cleanup()
                raise e
