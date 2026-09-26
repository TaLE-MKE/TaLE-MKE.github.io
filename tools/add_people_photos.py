#!/usr/bin/env python3
"""Add people's photos to the People page.

1. Put photos in photos-inbox/ (not published; it's in .gitignore), named after the
   person exactly as on the People page, e.g. "Kelly Barry.jpg". Accents are optional
   ("Isabella Kahhale.jpg" matches "Isabella Kahhalé"). JPG, PNG, WebP, and HEIC work.
2. Run from the site root:   python3 tools/add_people_photos.py
3. Each photo is square-cropped (centered, biased toward the top where faces usually
   are), resized to 320x320, saved as assets/img/people/<name>.webp with all metadata
   (EXIF, GPS) dropped, and swapped into that person's card in place of the initials.

Rerunning is safe: a newer photo replaces the old one. People without a photo keep
their initials. Names that don't match anyone on the page are reported and skipped.
"""
import argparse
import html as htmllib
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

SIZE = 320
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff"}


def fold(name):
    """Lowercase, strip accents and punctuation: 'Kahhalé' -> 'kahhale'."""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", n.lower()).strip()


def slug(name):
    return fold(name).replace(" ", "-")


def open_image(path):
    try:
        return Image.open(path)
    except Exception:
        # HEIC and other formats PIL can't read: convert with macOS sips.
        tmp = Path(tempfile.mkdtemp()) / (path.stem + ".png")
        subprocess.run(["sips", "-s", "format", "png", str(path), "--out", str(tmp)],
                       check=True, capture_output=True)
        return Image.open(tmp)


def square_crop(im):
    im = ImageOps.exif_transpose(im).convert("RGB")
    w, h = im.size
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * 0.2)  # portraits: keep the head, trim more from the bottom
    return im.crop((left, top, left + side, top + side)).resize((SIZE, SIZE), Image.LANCZOS)


ALUM_RE = re.compile(
    r'(<article class="alum">\s*)(<span class="avatar"[^>]*>[^<]*</span>|<img class="avatar avatar-photo"[^>]*>)'
    r'(\s*<div>\s*<h4>)([^<]+)(</h4>)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(Path(__file__).resolve().parent.parent))
    args = ap.parse_args()
    site = Path(args.site)
    inbox, outdir, page = site / "photos-inbox", site / "assets/img/people", site / "team.html"
    inbox.mkdir(exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)

    html = page.read_text()
    # Names in the page are HTML-escaped (e.g. O&#x27;Connor); decode before matching.
    people = {fold(htmllib.unescape(m.group(4))): htmllib.unescape(m.group(4)) for m in ALUM_RE.finditer(html)}
    photos = sorted(p for p in inbox.iterdir() if p.suffix.lower() in EXTS)

    added, unmatched = [], []
    for p in photos:
        key = fold(p.stem)
        if key not in people:
            unmatched.append(p.name)
            continue
        name = people[key]
        out = outdir / f"{slug(name)}.webp"
        square_crop(open_image(p)).save(out, quality=85, method=6)  # no exif= argument: metadata dropped
        added.append(name)

    def swap(m):
        name = htmllib.unescape(m.group(4))
        photo = outdir / f"{slug(name)}.webp"
        if not photo.exists():
            return m.group(0)
        img = (f'<img class="avatar avatar-photo" src="assets/img/people/{photo.name}" '
               f'width="160" height="160" alt="">')
        return m.group(1) + img + m.group(3) + m.group(4) + m.group(5)

    new = ALUM_RE.sub(swap, html)
    if new != html:
        page.write_text(new)

    with_photo = [n for n in people.values() if (outdir / f"{slug(n)}.webp").exists()]
    print(f"processed: {added or 'none'}")
    if unmatched:
        print(f"no one on the People page matches: {unmatched}  (rename to the name as shown on the page)")
    print(f"people with photos: {len(with_photo)}/{len(people)}")
    missing = [n for n in people.values() if n not in with_photo]
    if missing:
        print(f"still showing initials: {missing}")
    if added:
        print("next: python3 tools/stamp_assets.py && python3 tests/check_site.py, then review and push")
    return 1 if unmatched else 0


if __name__ == "__main__":
    sys.exit(main())
