from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def archive_and_new_session() -> dict:
    """Rollover the current session.
    i.e., archive the old session and start a new one.
    """
    return {"action": "archive_and_new_session"}
