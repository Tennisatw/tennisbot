from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def read_file(
    path: str) -> dict:
    """
    Read the contents of a file.

    Args:
        path (str): Path to the file.

    Returns:
        dict: {
            "success": bool,
            "content": str | None,
            "error": str | None,
        }
    """
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            contents = f.read()
        return {
            "success": True,
            "content": contents,
            "error": None,
        }
    except Exception as e:
        err = str(e)
        return {
            "success": False,
            "content": None,
            "error": err,
        }

