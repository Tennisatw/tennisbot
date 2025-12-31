import os
import fnmatch

from agents import function_tool
from src.logger import logged_tool


@function_tool
@logged_tool
async def list_files(
    root: str, 
    ignore: list[str] | None = None) -> dict:
    """
    Build a directory tree for AI coding agents.

    Args:
        root (str): Root directory.
        ignore (list[str] | None): Glob-style ignore patterns.
            default is [".git", "__pycache__", ".venv", "logs"].

    Returns:
        dict: Nested tree describing the filesystem:
            {
              "name": base name,
              "path": POSIX path relative to root ('.' for root),
              "type": "dir" | "file" | "symlink",
              "children": [ ... ] (dirs),
              "error": None | str (repr(Exception)),
            }
    """

    # defaults
    if ignore is None:
        ignore = [".git", "__pycache__", ".venv", "logs"]

    # normalize patterns
    norm_pats = [p.rstrip('/').rstrip('\\') for p in ignore]

    # helper to convert to posix path
    def to_posix(rel_path: str) -> str:
        if rel_path in ('', '.'):
            return '.'
        return rel_path.replace('\\', '/')

    def ignored(rel_path: str) -> bool:
        posix_rel = to_posix(rel_path)
        # derive base name from posix form to avoid Windows basename quirks with '/'
        base = posix_rel.rsplit('/', 1)[-1] if posix_rel != '.' else '.'

        for pat in norm_pats:
            if fnmatch.fnmatch(base, pat) or fnmatch.fnmatch(posix_rel, pat):
                return True
        return False

    abs_root = os.path.abspath(root)

    if not os.path.exists(abs_root):
        return {
            'name': os.path.basename(abs_root) or abs_root,
            'path': '.',
            'type': 'dir',
            'children': [],
            'error': f'Path not found: {abs_root}',
        }

    root_name = os.path.basename(abs_root) or abs_root

    # recursive builder
    def build(rel_path: str) -> dict:
        abs_path = os.path.join(abs_root, rel_path)
        name = root_name if not rel_path else (os.path.basename(abs_path) or root_name)

        try:
            if os.path.islink(abs_path):
                node_type = 'symlink'
            elif os.path.isdir(abs_path):
                node_type = 'dir'
            else:
                node_type = 'file'

            node = {
                'name': name,
                'path': to_posix(rel_path),
                'type': node_type,
                'children': [],
                'error': None,
            }

            if node_type == 'dir':
                try:
                    with os.scandir(abs_path) as it:
                        for entry in it:
                            child_rel = entry.name if not rel_path else os.path.join(rel_path, entry.name)

                            if ignored(child_rel):
                                continue
                            node['children'].append(build(child_rel))

                except Exception as e:
                    node['error'] = repr(e)

            return node

        except Exception as e:
            return {
                'name': name,
                'path': to_posix(rel_path),
                'type': 'file',
                'children': [],
                'error': repr(e),
            }

    return build('')
