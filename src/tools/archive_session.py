from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def archive_session() -> None:
    """Archive the current session and start a new session.
    Note: this is not "restart application".
    """
    # TODO: 新建agent总结会话，保存到data/session_summaries/yyyy-mm-dd_hh-mm-ss.md

    raise SystemExit(94)
