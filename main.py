from agents import SQLiteSession
import asyncio
import dotenv
import traceback

from src.agent import run
from src.load_agent import load_main_agent, load_sub_agents

# TODO: simplify imports

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
    # TODO: 支持保存session到文件中，以便下次接续会话
    session = SQLiteSession("tennisbot")
    
    # start the event loop
    while True:
        try:
            await run(agent, session)
        except (KeyboardInterrupt, SystemExit):
            print("Exiting...")
            break
        except asyncio.CancelledError:
            print("Task cancelled. Exiting...")
            break
        except Exception:
            print(f"Error occurred")
            traceback.print_exc()
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())