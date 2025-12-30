# Test list_files/grep tools

from pathlib import Path
import shutil
import sys
import json

import pytest

# Ensure repo root is importable so `import src...` works under pytest/uv on Windows
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools.list_files import list_files
from src.tools.grep import grep


@pytest.fixture(autouse=True)
def _cleanup_tmp_dirs():
    yield
    for p in ("tests/_tmp_grep", "tests/_tmp_grep_ignore", "tests/_tmp_grep_truncate"):
        shutil.rmtree(p, ignore_errors=True)


@pytest.mark.asyncio
async def test_list_files_respects_ignore_and_returns_tree():
    res = await list_files.on_invoke_tool(None, json.dumps({"root": ".", "ignore": ["tests"]})) # type: ignore
    assert res["error"] is None
    assert res["type"] == "dir"

    # Ensure ignored directory not present at root children
    child_names = {c["name"] for c in res["children"]}
    assert "tests" not in child_names


@pytest.mark.asyncio
async def test_grep_finds_literal_substring_and_is_deterministic():
    tmp_dir = Path("tests/_tmp_grep")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    f1 = tmp_dir / "a.txt"
    f2 = tmp_dir / "b.txt"
    f1.write_text("hello world\nHELLO world\n", encoding="utf-8")
    f2.write_text("x hello y\n", encoding="utf-8")

    res = await grep.on_invoke_tool(None, json.dumps({"query": "hello", "root": str(tmp_dir)})) # type: ignore
    assert res["error"] is None
    assert res["truncated"] is False

    # case_sensitive=False by default, so it should match both 'hello' and 'HELLO'
    assert res["matches"] == [
        {"file": "a.txt", "line": 1, "col": 1},
        {"file": "a.txt", "line": 2, "col": 1},
        {"file": "b.txt", "line": 1, "col": 3},
    ]


@pytest.mark.asyncio
async def test_grep_empty_query_returns_no_matches():
    res = await grep.on_invoke_tool(None, json.dumps({"query": "", "root": "."})) # type: ignore
    assert res["error"] is None
    assert res["matches"] == []
    assert res["truncated"] is False


@pytest.mark.asyncio
async def test_grep_respects_ignore():
    tmp_dir = Path("tests/_tmp_grep_ignore")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    (tmp_dir / "keep.txt").write_text("needle\n", encoding="utf-8")
    (tmp_dir / "skip.log").write_text("needle\n", encoding="utf-8")

    res = await grep.on_invoke_tool(None,json.dumps({"query": "needle", "root": str(tmp_dir), "ignore": ["*.log"]}),) # type: ignore

    assert res["matches"] == [{"file": "keep.txt", "line": 1, "col": 1}]


@pytest.mark.asyncio
async def test_grep_truncates_at_max_matches():
    tmp_dir = Path("tests/_tmp_grep_truncate")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 10 occurrences in one line
    (tmp_dir / "many.txt").write_text("aaaaaaaaaa\n", encoding="utf-8")

    res = await grep.on_invoke_tool(None,json.dumps({"query": "a", "root": str(tmp_dir), "max_matches": 3}),) # type: ignore

    assert res["truncated"] is True
    assert len(res["matches"]) == 3
