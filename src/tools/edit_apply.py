from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, Literal

from agents import function_tool
from src.logger import logged_tool



class Instruction(TypedDict, total=False):
    file: str
    op: Literal["replace", "insert_before", "insert_after"]
    anchor: str
    content: str
    match: str          # required when op == "replace"
    occurrence: int     # optional, default 1


@dataclass(frozen=True)
class _EditResult:
    success: bool
    file: str
    op: str
    anchor_hits: int
    changed: bool
    error: str | None
    preview_before: str
    preview_after: str

def _clip(s: str, *, max_len: int = 240) -> str:
    """Clip a string for previews."""
    if len(s) <= max_len:
        return s
    return s[:max_len] + "..."

def _find_nth(haystack: str, needle: str, occurrence: int) -> int:
    """Return the start index of the nth occurrence (1-based)."""
    if occurrence <= 0:
        return -1
    start = 0
    for _ in range(occurrence):
        idx = haystack.find(needle, start)
        if idx < 0:
            return -1
        start = idx + len(needle)
    return idx

def _count_occurrences(haystack: str, needle: str) -> int:
    """Count non-overlapping occurrences."""
    if needle == "":
        return 0
    return haystack.count(needle)

def _apply_one(text: str, inst: Instruction) -> tuple[str, _EditResult]:
    file = str(inst.get("file", ""))
    op = str(inst.get("op", ""))
    anchor = str(inst.get("anchor", ""))
    content = str(inst.get("content", ""))
    match = inst.get("match", None)
    occurrence = int(inst.get("occurrence", 1))

    if not file:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=0,
            changed=False,
            error="Missing required field: file",
            preview_before="",
            preview_after="",
        )

    if op not in {"replace", "insert_before", "insert_after"}:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=0,
            changed=False,
            error=f"Unsupported op: {op}",
            preview_before="",
            preview_after="",
        )

    if anchor == "":
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=0,
            changed=False,
            error="Missing required field: anchor",
            preview_before="",
            preview_after="",
        )

    hits = _count_occurrences(text, anchor)
    if hits == 0:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=0,
            changed=False,
            error="Anchor not found",
            preview_before="",
            preview_after="",
        )

    if occurrence <= 0 or occurrence > hits:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=False,
            error=f"Invalid occurrence: {occurrence} (hits={hits})",
            preview_before="",
            preview_after="",
        )

    anchor_idx = _find_nth(text, anchor, occurrence)
    if anchor_idx < 0:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=False,
            error="Failed to locate anchor occurrence",
            preview_before="",
            preview_after="",
        )

    if op == "insert_before":
        new_text = text[:anchor_idx] + content + text[anchor_idx:]
        return new_text, _EditResult(
            success=True,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=(new_text != text),
            error=None,
            preview_before=_clip(text[anchor_idx : anchor_idx + len(anchor)]),
            preview_after=_clip(new_text[anchor_idx : anchor_idx + len(content) + len(anchor)]),
        )

    if op == "insert_after":
        insert_at = anchor_idx + len(anchor)
        new_text = text[:insert_at] + content + text[insert_at:]
        return new_text, _EditResult(
            success=True,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=(new_text != text),
            error=None,
            preview_before=_clip(text[anchor_idx : anchor_idx + len(anchor)]),
            preview_after=_clip(new_text[anchor_idx : anchor_idx + len(anchor) + len(content)]),
        )

    # replace
    if not isinstance(match, str) or match == "":
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=False,
            error="Missing required field for replace: match",
            preview_before="",
            preview_after="",
        )

    match_idx = text.find(match, anchor_idx)
    if match_idx < 0:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=False,
            error="Match not found after anchor",
            preview_before=_clip(text[anchor_idx : anchor_idx + len(anchor)]),
            preview_after="",
        )

    new_text = text[:match_idx] + content + text[match_idx + len(match) :]
    return new_text, _EditResult(
        success=True,
        file=file,
        op=op,
        anchor_hits=hits,
        changed=(new_text != text),
        error=None,
        preview_before=_clip(text[match_idx : match_idx + len(match)]),
        preview_after=_clip(content),
    )

@function_tool
@logged_tool
async def edit_apply(
    instructions: list[Instruction],
    dry_run: bool = False,
) -> dict:
    """Apply anchored edit instructions to files.

    Notes:
        - This tool is a patchless alternative to unified diffs. Aimed at precise, small edits.
        - Each instruction targets a single file and uses an `anchor` to locate the edit.
        - For op=replace, `match` is required and will be replaced by `content`.

    Instruction schema:
        {
            "file": str,
            "op": "replace" | "insert_before" | "insert_after",
            "anchor": str,
            "content": str,
            "match": str,            # required for replace
            "occurrence": int,        # 1-based, default 1
        }

    Returns:
        dict: {
            "success": bool,
            "results": list[dict],
            "error": None | str,
        }
    """
    results: list = []
    any_fail = False

    for inst in instructions:
        file_path = str(inst.get("file", ""))
        if not file_path:
            results.append(
                {
                    "success": False,
                    "file": "",
                    "op": str(inst.get("op", "")),
                    "anchor_hits": 0,
                    "changed": False,
                    "error": "Missing required field: file",
                    "preview": {"before": "", "after": ""},
                }
            )
            any_fail = True
            continue

        p = Path(file_path)
        if not p.exists():
            results.append(
                {
                    "success": False,
                    "file": file_path,
                    "op": str(inst.get("op", "")),
                    "anchor_hits": 0,
                    "changed": False,
                    "error": f"File not found: {file_path}",
                    "preview": {"before": "", "after": ""},
                }
            )
            any_fail = True
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            results.append(
                {
                    "success": False,
                    "file": file_path,
                    "op": str(inst.get("op", "")),
                    "anchor_hits": 0,
                    "changed": False,
                    "error": f"Failed to read file: {repr(e)}",
                    "preview": {"before": "", "after": ""},
                }
            )
            any_fail = True
            continue

        new_text, r = _apply_one(text, inst)

        if r.success and (not dry_run) and r.changed:
            try:
                p.write_text(new_text, encoding="utf-8", errors="ignore")
            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "file": file_path,
                        "op": r.op,
                        "anchor_hits": r.anchor_hits,
                        "changed": False,
                        "error": f"Failed to write file: {repr(e)}",
                        "preview": {"before": r.preview_before, "after": r.preview_after},
                    }
                )
                any_fail = True
                continue

        results.append(
            {
                "success": r.success,
                "file": file_path,
                "op": r.op,
                "anchor_hits": r.anchor_hits,
                "changed": r.changed,
                "error": r.error,
                "preview": {"before": r.preview_before, "after": r.preview_after},
            }
        )

        if not r.success:
            any_fail = True

    return {
        "success": (not any_fail),
        "results": results,
        "error": None if not any_fail else "One or more instructions failed",
    }