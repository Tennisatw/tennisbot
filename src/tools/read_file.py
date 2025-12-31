from agents import function_tool

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
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            contents = f.read()
            return {
                "success": True,
                "content": contents,
                "error": None,
            }
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "error": str(e),
        }

