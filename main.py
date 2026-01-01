import asyncio
import dotenv

from src.run import run
from src.logger import logger

async def main():
    # load environment variables
    dotenv.load_dotenv()

    logger.setup()
    logger.log("app.start")

    # TODO: load settings

    # TODO: load schedule tasks
    
    # start the event loop
    await run()

    logger.log("app.end")


if __name__ == "__main__":
    asyncio.run(main())
