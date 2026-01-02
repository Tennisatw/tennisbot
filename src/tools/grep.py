import os
import fnmatch

from agents import function_tool
from src.logger import logged_tool
from src.settings import settings


@function_tool
@logged_tool
async def grep(
    query: str, 
    root: str = ".",
    ignore: list[str] | None = None,
    max_matches: int = 5000,
    case_sensitive: bool = False) -> dict:
    """
    Project grep utility: recursively search for a literal substring in text files.

    Args:
        query (str): Literal substring to find. Empty query returns no matches.
        root (str): Root directory to search from. Default "." (current working directory).
        ignore (list[str] | None): Glob-style ignore patterns applied to both base names and POSIX-relative paths.
            If None, uses default ignore patterns from settings.
            Ignored directories/files are skipped recursively.
        max_matches (int): Maximum number of total matches to return. Default 5000.
        case_sensitive (bool): Whether the search is case-sensitive. Default False.

    Returns:
        dict: {
            "success": bool,
            "query": str,
            "root": str,             # absolute normalized path of the searched root
            "matches": [
                { "file": str, "line": int, "col": int}
            ],
            "error": None | str,     # error message (e.g., root not found); otherwise None
            "truncated": bool,       # True if match limit reached
        }
    """

    # Early return for empty query
    if not query:
        abs_root = os.path.abspath(root)
        return {
            "success": True,
            "query": query,
            "root": abs_root,
            "matches": [],
            "error": None,
            "truncated": False,
        }

    # Defaults for ignore patterns
    if ignore is None:
        ignore = settings.default_ignore

    # Normalize ignore patterns (strip trailing slashes/backslashes)
    norm_pats = [p.rstrip('/').rstrip('\\') for p in ignore]

    # Helper: convert relative path to POSIX-style
    def to_posix(rel_path: str) -> str:
        if rel_path in ('', '.'):
            return '.'
        return rel_path.replace('\\', '/')

    # Helper: check if a relative path (POSIX) should be ignored
    def ignored(rel_path: str) -> bool:
        posix_rel = to_posix(rel_path)
        base = posix_rel.rsplit('/', 1)[-1] if posix_rel != '.' else '.'
        for pat in norm_pats:
            if fnmatch.fnmatch(base, pat) or fnmatch.fnmatch(posix_rel, pat):
                return True
        return False

    abs_root = os.path.abspath(root)

    # Root checks
    if not os.path.exists(abs_root):
        return {
            "success": False,
            "query": query,
            "root": abs_root,
            "matches": [],
            "error": f"Path not found: {abs_root}",
            "truncated": False,
        }
    if not os.path.isdir(abs_root):
        return {
            "success": False,
            "query": query,
            "root": abs_root,
            "matches": [],
            "error": f"Not a directory: {abs_root}",
            "truncated": False,
        }

    # Prepare search term according to case sensitivity
    needle = query if case_sensitive else query.lower()

    matches: list[dict] = []
    truncated = False

    # Walk the directory tree; prune ignored dirs and skip ignored files
    for dirpath, dirnames, filenames in os.walk(abs_root, followlinks=False):
        # Relative directory path from root
        rel_dir = os.path.relpath(dirpath, abs_root)

        # Prune ignored directories (sort for stable order)
        keep_dirs = []
        for d in sorted(dirnames):
            child_rel = d if rel_dir in ('', '.', None) else os.path.join(rel_dir, d)
            if not ignored(child_rel):
                keep_dirs.append(d)
        dirnames[:] = keep_dirs

        # Process files (sorted for stable order)
        for fname in sorted(filenames):
            rel_file = fname if rel_dir in ('', '.', None) else os.path.join(rel_dir, fname)
            if ignored(rel_file):
                continue

            abs_file = os.path.join(dirpath, fname)

            # Read file line-by-line. Use utf-8 with errors='ignore' to keep it simple and robust.
            try:
                with open(abs_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for lineno, line in enumerate(f, start=1):
                        hay = line if case_sensitive else line.lower()

                        # Find all occurrences in the line
                        start = 0
                        while True:
                            idx = hay.find(needle, start)
                            if idx == -1:
                                break

                            matches.append({
                                "file": to_posix(rel_file),
                                "line": lineno,
                                "col": idx + 1,  # 1-based column index
                            })

                            if len(matches) >= max_matches:
                                truncated = True
                                break

                            start = idx + 1  # allow overlapping search shift by 1

                        if truncated:
                            break

            except Exception as e:
                # Swallow file-specific errors and continue; we only record matches.
                # Keeping it simple: no per-file error reporting.
                continue

            if truncated:
                break

        if truncated:
            break

    # Ensure matches are ordered by file path, then line, then column (stable deterministic output)
    matches.sort(key=lambda m: (m["file"], m["line"], m["col"]))

    return {
        "success": True,
        "query": query,
        "root": abs_root,
        "matches": matches,
        "error": None,
        "truncated": truncated,
    }
