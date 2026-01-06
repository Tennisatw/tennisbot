import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass
class JsonlSession:
    """A minimal file-backed session store.

    Notes:
        - Stores items as JSON Lines (one JSON object per line).
        - Designed for single-writer per session_id.
        - pop_item() is intentionally not implemented.
    """

    session_id: str
    path: str | os.PathLike[str]

    def _path(self) -> Path:
        return Path(self.path)

    async def get_items(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Return stored items.

        Args:
            limit: Optional max number of items.
        """

        p = self._path()
        if not p.exists():
            return []

        items: list[dict[str, Any]] = []
        try:
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        # Ignore truncated/corrupted lines.
                        continue
                    if isinstance(obj, dict):
                        items.append(obj)
        except Exception:
            return []

        if isinstance(limit, int) and limit > 0:
            return items[-limit:]
        return items

    async def add_items(self, items: Iterable[dict[str, Any]]) -> None:
        """Append items to the session."""

        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)

        with p.open("a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False))
                f.write("\n")
            f.flush()
            os.fsync(f.fileno())

    async def pop_item(self) -> dict[str, Any]:
        raise NotImplementedError("pop_item is not supported by JsonlSession")

    async def clear_session(self) -> None:
        """Clear all stored items."""

        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text("", encoding="utf-8")
        os.replace(tmp, p)
