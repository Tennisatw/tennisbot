# 注：此工具会让Tennisbot产生极大的误解，包括 误以为交接时要先归档，弄混归档和重启，等等。
# 因此暂时弃用此工具。

from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def archive_session() -> None:
    """Archive the current session and start a new session.
    Note: this isn't an app restart.
    """
    # TODO: 新建agent总结会话，保存到data/session_summaries/yyyy-mm-dd_hh-mm-ss.md

    raise SystemExit(94)
