import shutil
import subprocess
from pathlib import Path

from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def draft_patch(
    patch: str,
    allow_reject: bool = False,
    ) -> dict:
    """
    Validate a unified diff patch str via `git apply --check --recount` and save it as draft.
    Note: Don't include the index line in the patch.
    Note: Patch hunks must include context lines.
    Args:
        patch (str): Unified diff string.
        allow_reject (bool): Whether to add --reject when using git apply --check. Default is False.
    Returns:
        dict: {
            "success": bool,
            "path": str | None,       # saved path if success
            "error": None | str,      # error message if failed
        }
    Git-style unified patch example:
```
diff --git a/agents/sub_agents/the_developer/template.txt b/agents/sub_agents/the_developer/template.txt
--- a/agents/sub_agents/the_developer/template.txt
+++ b/agents/sub_agents/the_developer/template.txt
@@ -1,2 +1,3 @@
 Hello Tennisbot
 Love from Tennisatw
+Hello world
```
    """

    if " a/" not in patch and " b/" not in patch:
        path_strip = 0
    else:
        path_strip = 1

    git_path = shutil.which("git")
    if not git_path:
        return {
            "success": False,
            "path": None,
            "error": "Git not found in PATH",
        }

    draft_path = Path("agents/sub_agents/the_developer/draft.patch")
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(patch, encoding="utf-8")

    cmd = [git_path, "apply", "--check", "--recount", f"-p{path_strip}"]
    if allow_reject:
        cmd.append("--reject")
    cmd.append(str(draft_path))

    proc = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0:
        return {
            "success": False,
            "path": str(draft_path),
            "error": f"Git apply check failed: {proc.stderr}",
        }

    return {
        "success": True,
        "path": str(draft_path),
        "error": None,
    }
