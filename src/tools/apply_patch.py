import os
import shutil
import subprocess
from pathlib import Path

from agents import function_tool

@function_tool
async def apply_patch(
    diff: str,
    tool: str = "git apply",
    ) -> dict:
    """
    Apply a unified diff patch to the current working directory using git apply.
    Note: diff have to be in git-style unified format.
    Args:
        diff (str): Unified diff string.
        tool (str): "git apply" or "patch". Tool to use for applying the patch. Default is "git apply".
    Returns:
        dict: {
            "success": bool,
            "tool": None | str,       # tool used
            "error": None | str,      # error message if failed
        }
    """
    print(f"Applying patch with diff:\n{diff}")

    if " a/" not in diff and " b/" not in diff:
        path_strip = 0
    else:
        path_strip = 1

    warnings = []
    # Lightweight path check: warn on absolute paths, drive letters, or '..'
    try:
        cwd = Path.cwd().resolve()
        for line in diff.splitlines():
            if line.startswith(("--- ", "+++ ")):
                path = line[4:].split("\t", 1)[0].strip()
                if path in ("/dev/null", "null", ""):
                    continue
                suspicious = False
                if os.path.isabs(path):
                    suspicious = True
                if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
                    suspicious = True
                if ".." in Path(path).parts:
                    suspicious = True
                try:
                    target = (cwd / Path(path)).resolve()
                    if not str(target).startswith(str(cwd)):
                        suspicious = True
                except Exception:
                    suspicious = True
                if suspicious:
                    warnings.append(f"Suspicious patch target path (warn only): {path}")
    except Exception as e:
        return {
            "success": False,
            "tool": None,
            "error": f"Failed to analyze patch paths: {repr(e)}",
        }

    encoding = "utf-8"

    if tool == "git apply":
        git_path = shutil.which("git")
        if git_path:
            check_proc = subprocess.run(
                [git_path, "apply", "--check", f"-p{path_strip}"],
                input=diff,
                text=True,
                encoding=encoding,
                capture_output=True,
                check=False,
                timeout=60,
            )
            if check_proc.returncode == 0:
                proc = subprocess.run(
                    [git_path, "apply", f"-p{path_strip}"],
                    input=diff,
                    text=True,
                    encoding=encoding,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                tool = "git"
                if proc.returncode == 0:
                    return {
                        "success": True,
                        "tool": tool,
                        "error": None,
                    }
                else:
                    return {
                        "success": False,
                        "tool": tool,
                        "error": f"Git apply failed: {proc.stderr}",
                    }
            else:
                return {
                    "success": False,
                    "tool": "git",
                    "error": f"Git apply check failed: {check_proc.stderr}",
                }

    elif tool == "patch":
        patch_path = shutil.which("patch")
        if patch_path:
            proc = subprocess.run(
                [patch_path, f"-p{path_strip}"],
                input=diff,
                text=True,
                encoding=encoding,
                capture_output=True,
                check=False,
                timeout=60,
            )
            tool = "patch"
            if proc.returncode == 0:
                return {
                    "success": True,
                    "tool": tool,
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "tool": tool,
                    "error": f"Patch command failed: {proc.stderr}",
                }

    else:
        return {
            "success": False,
            "error": f"Unsupported tool: {tool}",
        }
    
    return {
        "success": False,
        "tool": None,
        "error": "No suitable patching tool found (git or patch)",
    }
