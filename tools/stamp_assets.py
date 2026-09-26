#!/usr/bin/env python3
"""Stamp css/styles.css and js/main.js links with a content hash (?v=...).

GitHub Pages tells browsers to cache files for 10 minutes. Without a version,
a visitor can get new HTML with an old stylesheet. The hash changes whenever
the file changes, so browsers fetch the new copy right away.

Run from the site root after editing CSS or JS:
    python3 tools/stamp_assets.py
tests/check_site.py fails if a stamp is missing or stale.
"""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ["css/styles.css", "js/main.js"]


def version(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:10]


def stamp(html):
    for asset in ASSETS:
        html = re.sub(rf'(["\']){re.escape(asset)}(\?v=[0-9a-f]+)?(["\'])',
                      rf'\g<1>{asset}?v={version(asset)}\g<3>', html)
    return html


if __name__ == "__main__":
    changed = []
    for page in sorted(ROOT.glob("*.html")):
        old = page.read_text()
        new = stamp(old)
        if new != old:
            page.write_text(new)
            changed.append(page.name)
    print("versions:", {a: version(a) for a in ASSETS})
    print("updated:", changed or "nothing (already current)")
