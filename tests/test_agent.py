# 测试agent可以正常创建/运行

from agents import Agent, Runner
import asyncio
import dotenv
import pytest

@pytest.mark.asyncio
async def test_agent_run():
    dotenv.load_dotenv()
    agent = Agent(
        name="Tennisbot",
        instructions="",
        model = "gpt-5-mini",
        tools=[],
    )
    result = await Runner.run(agent, "请输出“我是Tennisbot”")
    assert "我是Tennisbot" in result.final_output
    

if __name__ == "__main__":
    asyncio.run(test_agent_run())