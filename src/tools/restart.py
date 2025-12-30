from agents import function_tool


@function_tool
async def restart(code: int = 94) -> None:
    """Exit the program with a specific exit code.

    Args:
        code: Any code other than STOP_CODE (95) will trigger restart in start.bat.
    """
    raise SystemExit(code)

