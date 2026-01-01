from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def archive_and_new_session() -> None:
    """Rollover the current session. i.e., archive the old session and start a new one.
    """
    raise SystemExit(94)
