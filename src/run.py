from agents import Runner

async def run(agent, session):
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting the event loop.")
            raise KeyboardInterrupt
        result = await Runner.run(
            agent, 
            user_input,
            session = session,
            max_turns=30,
        )
        print(f"Tennisbot: {result.final_output}")

        # TODO：每次会话半小时后，自动保存会话，并创建新会话
        # TODO: 异步会话，允许同时处理多个用户请求
