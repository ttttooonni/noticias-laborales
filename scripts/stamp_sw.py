#!/usr/bin/env python3
"""Rewrite the CACHE constant in sw.js from a hash of the app shell."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SW = ROOT / "sw.js"
FILES = [ROOT / "index.html", ROOT / "app.js", ROOT / "styles.css"]


def main() -> None:
    if not SW.exists():
        print("no sw.js; skip")
        return
    h = hashlib.sha1()
    for p in FILES:
        if p.exists():
            h.update(p.read_bytes())
    stamp = h.hexdigest()[:12]
    text = SW.read_text(encoding="utf-8")
    new, n = re.subn(
        r"const CACHE\s*=\s*['\"]noticias-laborales-[^'\"]+['\"]",
        f"const CACHE = 'noticias-laborales-{stamp}'",
        text,
        count=1,
    )
    if n == 0:
        new = f"const CACHE = 'noticias-laborales-{stamp}';\n" + text
    if new != text:
        SW.write_text(new, encoding="utf-8")
        print(f"sw cache → noticias-laborales-{stamp}")
    else:
        print(f"sw cache unchanged ({stamp})")


if __name__ == "__main__":
    main()
