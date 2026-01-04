from __future__ import annotations

from pathlib import Path

TEXT_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".svelte", ".css", ".scss", ".html",
    ".md", ".json", ".yml", ".yaml", ".toml",
    ".txt",
}

def classify_newlines(data: bytes) -> str:
    has_crlf = b"\r\n" in data
    has_lf = b"\n" in data
    has_cr = b"\r" in data

    if not has_lf and not has_cr:
        return "no-newline"
    if has_crlf and not (has_lf and not has_crlf) and not (has_cr and not has_crlf):
        return "crlf"
    if has_lf and not has_cr:
        return "lf"
    return "mixed"

def main(root: str = ".", *, exts: set[str] | None = None) -> None:
    root_path = Path(root).resolve()
    exts = exts or TEXT_EXTS

    counts: dict[str, int] = {"crlf": 0, "lf": 0, "mixed": 0, "no-newline": 0}
    bad: list[tuple[str, str]] = []

    for p in root_path.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue

        data = p.read_bytes()
        kind = classify_newlines(data)
        counts[kind] += 1

        if kind != "crlf":
            bad.append((str(p.relative_to(root_path)), kind))

    print("== newline summary ==")
    for k in ("crlf", "lf", "mixed", "no-newline"):
        print(f"{k:10s}: {counts[k]}")

    print("\n== non-CRLF files ==")
    for rel, kind in bad:
        print(f"{kind:10s} {rel}")

if __name__ == "__main__":
    main("web/backend")