# 有点鸡肋的功能。首先，所有run_python能做的工作，都可以run_shell完成。其次，本功能很危险。

import sys

from agents import function_tool
from src.logger import logged_tool

class StdoutRedirect:

    def __init__(self):
        self.content = ''

    def write(self, text):
        self.content += text

    def flush(self):
        pass


@function_tool
@logged_tool
async def run_python(
    command: str,
) -> dict:
    """Execute Python code via exec() in current process

    Note: Avoid using this tool unless absolutely necessary. Please check with user before using.
    Intended for runtime debugging and may contaminate global variables. Use with caution.

    Args:
        command: Command string.

    Returns:
        dict: {
            "success": bool,
            "output": str,
            "error": None | str,      # error message if failed
        }
    """
    stdout = StdoutRedirect()
    try:
        sys.stdout = stdout
        exec(command, globals(), locals())
        return {
            "success": True,
            "output": stdout.content,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "output": stdout.content,
            "error": str(e),
        }
    finally:
        sys.stdout = sys.__stdout__
