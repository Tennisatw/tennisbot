import subprocess

from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def run_shell(
    command: str,
    shell: str = "powershell",
    cwd: str | None = None,
    timeout_sec: int = 60,
) -> dict:
    """Run a shell command. Use with caution.

    Args:
        command: Command string.
        shell: "powershell" | "cmd".
        cwd: Working directory, or None to use current directory. default is None.
        timeout_sec: Timeout in seconds, default is 60 seconds.

    Returns:
        dict: {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "exit_code": int,
        }
    """

    if shell == "cmd":
        args = ["cmd", "/c", command]
    else:
        # Windows PowerShell (5.1) is widely available on Windows.
        args = ["powershell", "-NoProfile", "-Command", command]

    try:
        cp = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return {
            "success": cp.returncode == 0,
            "stdout": cp.stdout or "",
            "stderr": cp.stderr or "",
            "exit_code": cp.returncode,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "success": False,
            "stdout": getattr(e, "stdout", "") or "",
            "stderr": getattr(e, "stderr", "") or "timeout",
            "exit_code": -1,
        }
