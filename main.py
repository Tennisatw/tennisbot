from agents import SQLiteSession
import asyncio
import dotenv

from src.run import run
from src.load_agent import create_handoff_obj, load_main_agent, load_sub_agents
from src.logger import logger

async def main():
    # load environment variables
    dotenv.load_dotenv()

    logger.setup()
    logger.log("app.start")

    # TODO: load settings

    # TODO: load schedule tasks

    # load agents and handoffs
    agent = load_main_agent()
    agent_handoff_obj = create_handoff_obj(agent)
    agents_list = load_sub_agents(handoffs=[agent_handoff_obj])
    agent.handoffs = [create_handoff_obj(sub_agent) for sub_agent in agents_list]

    # Create a session
    # TODO: 保存session到文件中，以便下次接续会话
    session = SQLiteSession("tennisbot")
    
    # start the event loop
    await run(agent, session)

    logger.log("app.end")


if __name__ == "__main__":
    asyncio.run(main())
