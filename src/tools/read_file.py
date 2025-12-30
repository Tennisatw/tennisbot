from agents import function_tool

@function_tool
async def read_file(
    path: str) -> str:
    """
    Read the contents of a file.

    Args:
        path (str): Path to the file.

    Returns:
        str: Contents of the file.
    """
    print(f"Reading file: {path}")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()