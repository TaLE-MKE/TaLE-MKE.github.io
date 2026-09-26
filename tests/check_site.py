#!/usr/bin/env python3
"""Static checks for the TaLE MKE site. Standard library only.

Run from the site root:  python3 tests/check_site.py
Exits non-zero on any failure. Also prints how many PLACEHOLDER markers remain.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "research.html", "team.html", "publications.html", "news.html", "contact.html"]
failures = []


def fail(msg):
    failures.append(msg)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.title = ""
        self._in_title = False
        self.h1 = 0
        self.imgs = []
        self.links = []
        self.srcs = []
        self.ids = set()
        self.nav_links = []
        self.current = []
        self._in_nav = False
        self.labels_for = set()
        self.inputs = []
        self.has_main = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "main":
            self.has_main = True
        elif tag == "img":
            self.imgs.append(a)
            self.srcs.append(a.get("src", ""))
        elif tag == "nav" and a.get("id") == "site-nav":
            self._in_nav = True
        elif tag == "a":
            self.links.append(a.get("href", ""))
            if self._in_nav:
                self.nav_links.append(a.get("href"))
                if a.get("aria-current") == "page":
                    self.current.append(a.get("href"))
        elif tag in ("link", "script"):
            ref = a.get("href") or a.get("src")
            if ref:
                self.srcs.append(ref)
        elif tag == "label" and "for" in a:
            self.labels_for.add(a["for"])
        elif tag in ("input", "textarea"):
            self.inputs.append(a.get("id"))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "nav":
            self._in_nav = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def is_local(ref):
    return ref and not re.match(r"^(https?:|mailto:|#|data:)", ref)


def luminance(hex_color):
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---- per-page checks ----
parsed = {}
for name in PAGES:
    path = ROOT / name
    if not path.exists():
        fail(f"{name}: missing")
        continue
    p = Page()
    p.feed(path.read_text())
    parsed[name] = p

    if p.lang != "en":
        fail(f"{name}: <html> needs lang=\"en\"")
    if not p.title.strip():
        fail(f"{name}: empty <title>")
    if p.h1 != 1:
        fail(f"{name}: expected exactly 1 <h1>, found {p.h1}")
    if not p.has_main or "main" not in p.ids:
        fail(f"{name}: needs <main id=\"main\"> for the skip link")
    for img in p.imgs:
        if "alt" not in img:
            fail(f"{name}: <img src={img.get('src')}> has no alt attribute")
    if p.current != [name]:
        fail(f"{name}: nav aria-current should mark only {name}, got {p.current}")
    for ref in p.srcs + p.links:
        if is_local(ref):
            target = ROOT / ref.split("#")[0]
            if not target.exists():
                fail(f"{name}: broken local reference {ref}")
        if ref.startswith("http") and "fonts.g" not in ref and "formspree" not in ref:
            # External assets other than Google Fonts are not allowed.
            if ref in p.srcs:
                fail(f"{name}: external asset {ref} (only Google Fonts allowed)")
    for href in p.links:
        if "#" in href and not href.startswith("#") and is_local(href):
            page, frag = href.split("#", 1)
            if frag and page in parsed and frag not in parsed[page].ids:
                fail(f"{name}: anchor {href} not found")
    for input_id in p.inputs:
        if input_id not in p.labels_for:
            fail(f"{name}: form control #{input_id} has no <label for>")
    if "—" in path.read_text():
        fail(f"{name}: contains an em dash")

# Every page has the same nav in the same order.
navs = {n: tuple(p.nav_links) for n, p in parsed.items()}
if len(set(navs.values())) != 1:
    fail(f"nav differs across pages: {navs}")
elif list(navs.values())[0] != tuple(PAGES):
    fail(f"nav order {list(navs.values())[0]} != {PAGES}")

# Late-bound anchor check (pages parsed after the linking page).
for name, p in parsed.items():
    for href in p.links:
        if "#" in href and is_local(href):
            page, frag = href.split("#", 1)
            if frag and page in parsed and frag not in parsed[page].ids:
                fail(f"{name}: anchor {href} not found")

# Footer names both institutions on every page.
for name in parsed:
    html = (ROOT / name).read_text()
    footer = html[html.find("<footer"):]
    for inst in ("Medical College of Wisconsin", "Children's Wisconsin"):
        if inst not in footer:
            fail(f"{name}: footer is missing {inst}")

# ---- color contrast (WCAG AA 4.5:1 for normal text) ----
css = (ROOT / "css/styles.css").read_text()
tokens = dict(re.findall(r"--(color-[\w-]+):\s*(#[0-9a-fA-F]{6})", css))
pairs = [
    ("#ffffff", "color-primary", "white text on primary buttons/nav"),
    ("#ffffff", "color-primary-dark", "footer text"),
    ("#ffffff", "color-secondary", "secondary on white (links)"),
    ("color-text", "color-bg", "body text"),
    ("color-text-muted", "color-bg", "muted text"),
    ("color-text-muted", "color-warm", "muted text on warm band"),
    ("color-text-muted", "color-primary-soft", "muted text on tint"),
    ("color-primary", "color-primary-soft", "role pill / eyebrow on tint"),
    ("color-secondary-dark", "color-secondary-soft", "role pill (even cards)"),
    ("color-secondary", "color-secondary-soft", "links in note box"),
    ("color-error", "color-bg", "form errors"),
    ("color-success", "color-bg", "form success"),
]
print("Contrast (WCAG AA needs 4.5):")
for fg, bg, label in pairs:
    f = tokens.get(fg, fg)
    b = tokens.get(bg, bg)
    ratio = contrast(f, b)
    print(f"  {ratio:5.2f}  {label}")
    if ratio < 4.5:
        fail(f"contrast {ratio:.2f} < 4.5 for {label} ({f} on {b})")

# ---- report ----
placeholders = sum((ROOT / n).read_text().count("PLACEHOLDER") for n in PAGES)
placeholders += css.count("PLACEHOLDER")
print(f"\nPLACEHOLDER markers remaining: {placeholders} (grep -rn PLACEHOLDER . to list them)")

if failures:
    print(f"\nFAIL ({len(failures)}):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(f"\nPASS: {len(PAGES)} pages checked")
