#!/usr/bin/env python3
"""
i18n coverage scanner for the CrimeNet AI frontend.

Finds user-facing English string literals that are still hardcoded in TSX,
so translation coverage can be measured objectively instead of by eye.

Heuristics (deliberately conservative — it over-reports rather than hides):
  * JSX text nodes between tags
  * string literals assigned to human-visible props
    (label, title, subtitle, placeholder, message, hint, tagline,
     description, aria-label)
It ignores: className/style/icon/tone/to/type/id/key/name props, import
paths, API routes, identifiers (ALL_CAPS_TOKENS), pure numbers/punctuation,
and anything inside src/i18n/ (those files ARE the translations).

Usage:  python3 tools/i18n_scan.py [--list FILE]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "src"

VISIBLE_PROPS = (
    "label|title|subtitle|placeholder|message|hint|tagline|description|"
    "aria-label|caption|heading|text|emptyText|confirmLabel|cancelLabel"
)

PROP_RE = re.compile(rf'\b(?:{VISIBLE_PROPS})=(?:"([^"]{{2,}})"|\'([^\']{{2,}})\')')
JSX_TEXT_RE = re.compile(r">\s*([A-Z][A-Za-z][^<>{}\n]{2,})\s*<")
# object-literal copy: { title: 'Run extraction', detail: "…" }
OBJ_RE = re.compile(rf"\b(?:{VISIBLE_PROPS}|detail|note|question|summary|statement|body|copy|reason|stage|step)\s*:\s*(?:\"([^\"]{{3,}})\"|'([^']{{3,}})')")

SKIP_DIRS = {"i18n"}
IDENT_RE = re.compile(r"^[A-Z0-9_\-./:+ ]+$")          # SHA-256, CASE-101, POST …
HAS_LETTERS_RE = re.compile(r"[A-Za-z]{2,}")


def is_translatable(text: str) -> bool:
    t = text.strip()
    if len(t) < 3:
        return False
    if not HAS_LETTERS_RE.search(t):
        return False
    if IDENT_RE.match(t):                                # pure identifier/token
        return False
    if t.startswith(("/", "http", "#", "{")):            # routes, urls
        return False
    if t in {"true", "false", "null"}:
        return False
    return True


def scan_file(path: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("//", "*", "/*", "import ")):
            continue
        for m in PROP_RE.finditer(line):
            val = m.group(1) or m.group(2) or ""
            if is_translatable(val):
                hits.append((n, val))
        for m in OBJ_RE.finditer(line):
            val = m.group(1) or m.group(2) or ""
            if is_translatable(val):
                hits.append((n, val))
        for m in JSX_TEXT_RE.finditer(line):
            val = m.group(1)
            if is_translatable(val):
                hits.append((n, val))
    return hits


def main() -> int:
    if not ROOT.exists():
        print(f"no such directory: {ROOT}", file=sys.stderr)
        return 2

    show = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--list" else None
    rows: list[tuple[int, str]] = []
    total = 0

    for f in sorted(ROOT.rglob("*.tsx")) + sorted(ROOT.rglob("*.ts")):
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        hits = scan_file(f)
        rel = str(f.relative_to(ROOT))
        if show and show in rel:
            for n, v in hits:
                print(f"{rel}:{n}: {v}")
        if hits:
            rows.append((len(hits), rel))
        total += len(hits)

    if not show:
        rows.sort(reverse=True)
        print(f"{'residual':>9}  file")
        print("-" * 60)
        for count, rel in rows:
            print(f"{count:>9}  {rel}")
        print("-" * 60)
        print(f"{total:>9}  TOTAL residual hardcoded strings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
