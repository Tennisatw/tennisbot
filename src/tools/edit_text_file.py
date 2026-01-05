import os

from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def edit_text_file(
    path: str, 
    content: str,
    mode: str = "a"
    ) -> dict:
    """
    Append/Overwrite the contents to a text file. This tool provide a simple way for maintaining memos, generating reports, etc.
    Can only edit .txt, and .md files. 
    Args:
        path (str): Path to the file.
        content (str): Content to write to the file.
        mode (str): File open mode, default is "a" for append. Use "w" to overwrite.

    Returns:
        dict: {
            "success": bool,
            "error": None | str,      # error message if failed
        }
    """
    try:
        if not (path.endswith(".txt") or path.endswith(".md")):
            return {
                "success": False,
                "error": "Can only append to .txt or .md files.",
            }

        dirpath = os.path.dirname(path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(path, mode, encoding="utf-8", errors="ignore") as f:
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