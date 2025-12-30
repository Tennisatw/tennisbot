import shutil
import subprocess
from pathlib import Path

from agents import function_tool


@function_tool
async def draft_patch(
    patch: str,
    ) -> dict:
    """
    Validate a unified diff patch via `git apply --check` and save it as draft.
    Note: Don't include the index line in the patch.
    Args:
        patch (str): Unified diff string.
    Returns:
        dict: {
            "success": bool,
            "path": str | None,       # saved path if success
            "error": None | str,      # error message if failed
        }
    Git-style unified patch example:
```
diff --git a/agents/sub_agents/developer/template.txt b/agents/sub_agents/developer/template.txt
--- a/agents/sub_agents/developer/template.txt
+++ b/agents/sub_agents/developer/template.txt
@@ -1,2 +1,3 @@
 Hello Tennisbot
 Love from Tennisatw
+Hello world
```
    """
    print(f"Drafting patch:\n{patch}")

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

    draft_path = Path("agents/sub_agents/developer/draft.patch")
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(patch, encoding="utf-8")

    proc = subprocess.run(
        [git_path, "apply", "--check", "--ignore-whitespace", "--recount", f"-p{path_strip}", str(draft_path)],
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
