import os

from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def write_file(
    path: str, 
    content: str
    ) -> dict:
    """
    Write the contents to a file.
    Note: Avoid using this tool unless absolutely necessary. Please check with user before writing to any files.
    Args:
        path (str): Path to the file.
        content (str): Content to write to the file.

    Returns:
        dict: {
            "success": bool,
            "error": None | str,      # error message if failed
        }
    """
    try:
        dirpath = os.path.dirname(path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        with open(path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)
        return {
            "success": True,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }