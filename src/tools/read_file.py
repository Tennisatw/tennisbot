from agents import function_tool
from src.logger import logger


@function_tool
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
    print(f"Reading file: {path}")
    logger.log("tool.read_file.input", path=path)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            contents = f.read()

        logger.log("tool.read_file.output", success=True, content_preview=contents, content_len=len(contents))

        return {
            "success": True,
            "content": contents,
            "error": None,
        }
    except Exception as e:
        err = str(e)
        logger.log("tool.read_file.output", success=False, error=err)
        return {
            "success": False,
            "content": None,
            "error": err,
        }

