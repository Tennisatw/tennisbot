from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def write_file(
    path: str, content: str) -> dict:
    """
    Write the contents to a file.
    Note: Avoid using this tool unless absolutely necessary. Please check with the user before writing to any files.
    Args:
        path (str): Path to the file.
        content (str): Content to write to the file.

    Returns:
        dict: {
            "success": bool,
            "path": str,
            "error": None | str,      # error message if failed
        }
    """
    try:
        with open(path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(content)
        return {
            "success": True,
            "path": path,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "path": path,
            "error": str(e),
        }