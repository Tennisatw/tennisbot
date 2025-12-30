from agents import Agent, Runner
import asyncio
import dotenv

dotenv.load_dotenv()

agent2 = Agent(
    name="Tennisbot_the_Developer",
    instructions="请回答所有有关编程的问题。在回答完毕后，输出你的名字",
    model = "gpt-5-mini",
    tools=[],
)
agent1 = Agent(
    name="Tennisbot_Generalist",
    instructions="请将所有有关编程的问题交给Tennisbot-the-Developer处理。在每次回答完毕后，输出你的名字",
    model = "gpt-5-mini",
    tools=[],
    handoffs = [agent2]
)

result = asyncio.run(Runner.run(agent1, "python怎么打印hello world？"))
print( result.final_output.strip() )
result = asyncio.run(Runner.run(agent1, "请输出“今天温度为15-25度”"))
print( result.final_output.strip() )
