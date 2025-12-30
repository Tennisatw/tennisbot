from agents import function_tool

@function_tool
async def write_file(
    path: str, content: str) -> None:
    """
    Write the contents to a file.

    Args:
        path (str): Path to the file.
        content (str): Content to write to the file.

    Returns:
        None
    """
    print(f"Writing to file: {path}")
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(content)