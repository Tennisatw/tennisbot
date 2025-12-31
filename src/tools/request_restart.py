from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def request_restart(mode: str = "restart") -> None:
    """Request the launcher to restart or exit the program.

    This tool terminates the current process by raising ``SystemExit`` with a
    special exit code that is interpreted by the launcher (``start.bat``):

    Args:
        mode: Restart/exit selector.
            - "restart" (default)
            - "exit"/"quit"
    """
    if mode in ("exit", "quit"):
        exit_code = 95
    else:
        exit_code = 96

    raise SystemExit(exit_code)
