from agents import function_tool
from src.logger import logged_tool
from src.globals import SessionRolloverError


@function_tool
@logged_tool
async def rollover_session() -> None:
    """Rollover the current session, to archive it and start a new one.
    """
    raise SessionRolloverError()