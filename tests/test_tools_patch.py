# Test draft_patch/apply_patch tools

from pathlib import Path
import uuid
import sys
import json

import pytest

# Ensure repo root is importable so `import src...` works under pytest/uv on Windows
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.apply_patch import apply_patch
from src.tools.draft_patch import draft_patch


@pytest.mark.asyncio
async def test_draft_patch_and_apply_patch_roundtrip():
    tmp_file = Path("tests/_tmp_patch_tool") / f"{uuid.uuid4().hex}.txt"
    rel_path = tmp_file.as_posix()

    create_patch = (
        f"diff --git a/{rel_path} b/{rel_path}\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        f"+++ b/{rel_path}\n"
        "@@ -0,0 +1,1 @@\n"
        "+hello patch tool\n"
    )

    res = await draft_patch.on_invoke_tool(None, json.dumps({"patch": create_patch})) # type: ignore
    assert res["success"] is True
    assert res["path"]

    res = await apply_patch.on_invoke_tool(None, json.dumps({"patch_path": res["path"], "tool": "git apply"})) # type: ignore
    assert res["success"] is True
    assert tmp_file.exists()
    assert tmp_file.read_text(encoding="utf-8") == "hello patch tool\n"

    delete_patch = (
        f"diff --git a/{rel_path} b/{rel_path}\n"
        "deleted file mode 100644\n"
        f"--- a/{rel_path}\n"
        "+++ /dev/null\n"
        "@@ -1,1 +0,0 @@\n"
        "-hello patch tool\n"
    )

    res = await draft_patch.on_invoke_tool(None, json.dumps({"patch": delete_patch})) # type: ignore
    assert res["success"] is True

    res = await apply_patch.on_invoke_tool(None, json.dumps({"patch_path": res["path"], "tool": "git apply"})) # type: ignore
    assert res["success"] is True
    assert not tmp_file.exists()
