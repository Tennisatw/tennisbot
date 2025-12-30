from agents import SQLiteSession
import asyncio
import dotenv

from src.run import run
from src.load_agent import load_main_agent, load_sub_agents

async def main():
    # load environment variables
    dotenv.load_dotenv()

    # TODO: start logging

    # TODO: load settings

    # TODO: load schedule tasks

    # load agents
    agent = load_main_agent()
    agents_list = load_sub_agents(handoffs=[agent])
    agent.handoffs = agents_list

    # Create a session
    # TODO: 保存session到文件中，以便下次接续会话
    session = SQLiteSession("tennisbot")
    
    # start the event loop
    await run(agent, session)


if __name__ == "__main__":
    asyncio.run(main())
