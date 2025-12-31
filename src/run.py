from agents import Runner

async def run(agent, session):
    
    # Keep the active agent across turns.
    # Handoffs only affect the current Runner.run() call unless we persist it.
    current_agent = agent

    while True:
        user_input = input("User: ")
        result = await Runner.run(
            current_agent,
            user_input,
            session = session,
            max_turns=30,
        )

        last_agent = getattr(result, "last_agent", None)
        if last_agent is not None:
            current_agent = last_agent

        name = getattr(current_agent, "name", "Agent")
        print(f"{name}: {result.final_output}")

        # TODO：每次会话15分钟后，自动保存会话，并创建新会话
        # TODO: 异步会话，允许同时处理多个用户请求
