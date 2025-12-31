import shutil
import subprocess
from pathlib import Path

from agents import function_tool


@function_tool
async def apply_patch(
    patch_path: str,
    tool: str = "git apply",
    ) -> dict:
    """
    Apply a unified diff patch file to the current working directory.
    Args:
        patch_path (str): Patch file path.
        tool (str): "git apply" or "patch". Tool to use for applying the patch. Default is "git apply".
    Returns:
        dict: {
            "success": bool,
            "tool": None | str,       # tool used
            "error": None | str,      # error message if failed
        }
    """
    patch_file = Path(patch_path)
    print(f"Applying patch file: {patch_file}")

    if not patch_file.exists():
        return {
            "success": False,
            "tool": None,
            "error": f"Patch file not found: {patch_file}",
        }

    try:
        patch_text = patch_file.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "tool": None,
            "error": f"Failed to read patch file: {repr(e)}",
        }

    if " a/" not in patch_text and " b/" not in patch_text:
        path_strip = 0
    else:
        path_strip = 1

    if tool == "git apply":
        git_path = shutil.which("git")
        if git_path:
            check_proc = subprocess.run(
                [git_path, "apply", "--check", "--recount", f"-p{path_strip}", str(patch_file)],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
                timeout=60,
            )
            if check_proc.returncode == 0:
                proc = subprocess.run(
                    [git_path, "apply", "--recount", f"-p{path_strip}", str(patch_file)],
                    text=True,
                    encoding="utf-8",
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
        patch_bin = shutil.which("patch")
        if patch_bin:
            proc = subprocess.run(
                [patch_bin, f"-p{path_strip}", "-i", str(patch_file)],
                text=True,
                encoding="utf-8",
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
