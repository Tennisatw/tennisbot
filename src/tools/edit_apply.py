from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, Literal
import re


from agents import function_tool
from src.logger import logged_tool



class Instruction(TypedDict, total=False):
    file: str
    op: Literal["replace", "insert_before", "insert_after"]
    anchor: str
    content: str
    match: str          # required when op == "replace"


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

    # Guardrail: anchor must be unique.
    # This avoids ambiguous edits when the same anchor appears multiple times.
    if hits != 1:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=False,
            error=f"Anchor not unique (hits={hits})",
            preview_before="",
            preview_after="",
        )


    anchor_idx = text.find(anchor)
    if anchor_idx < 0:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=False,
            error="Failed to locate anchor",
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

    window = text[anchor_idx : anchor_idx + 8192]

    if match.startswith("re:"):
        pattern = match[3:]
        try:
            m = re.search(pattern, window, flags=re.MULTILINE)
        except re.error as e:
            return text, _EditResult(
                success=False,
                file=file,
                op=op,
                anchor_hits=hits,
                changed=False,
                error=f"Invalid regex: {e}",
                preview_before=_clip(text[anchor_idx : anchor_idx + len(anchor)]),
                preview_after="",
            )

        if m is None:
            return text, _EditResult(
                success=False,
                file=file,
                op=op,
                anchor_hits=hits,
                changed=False,
                error="Match not found after anchor (regex)",
                preview_before=_clip(text[anchor_idx : anchor_idx + len(anchor)]),
                preview_after="",
            )

        a, b = m.span()
        new_text = (
            text[:anchor_idx]
            + window[:a]
            + content
            + window[b:]
            + text[anchor_idx + len(window) :]
        )
        return new_text, _EditResult(
            success=True,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=(new_text != text),
            error=None,
            preview_before=_clip(window[a:b]),
            preview_after=_clip(content),
        )

    # Literal match
    rel = window.find(match)
    if rel < 0:
        return text, _EditResult(
            success=False,
            file=file,
            op=op,
            anchor_hits=hits,
            changed=False,
            error="Match not found after anchor (match is a literal substring; use re:... for regex)",
            preview_before=_clip(text[anchor_idx : anchor_idx + len(anchor)]),
            preview_after="",
        )

    match_idx = anchor_idx + rel
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
        - Try providing 2-3 lines for the anchor to ensure uniqueness.
        - For op=replace, `match` is required and will be replaced by `content`.

    Instruction schema:
        {
            "file": str,
            "op": "replace" | "insert_before" | "insert_after",
            "anchor": str,
            "content": str,
            "match": str,            # required for replace
        }

    Match behavior:
        - Literal: `match` is treated as a literal substring.
        - Regex: prefix with `re:` to treat the rest as a Python regex (searched only within a small window after `anchor`).

        Example:
            {
                "file": "src/app.py",
                "op": "replace",
                "anchor": "def foo():",
                "match": "re:return\\s+\\d+",
                "content": "return 0",
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