#!/usr/bin/env python3
"""Rebuild the publication list on publications.html from Jamie's CV.

Usage (macOS, from the site root):
    python3 tools/update_publications.py path/to/Hanson_CV.docx
    python3 tools/update_publications.py path/to/cv.txt      # plain text also works

What it does:
  1. Reads the CV (.docx via macOS `textutil`, or .txt).
  2. Parses "Peer-Reviewed Journal Articles", "Book Chapters", and
     "Journal Commentaries" entries of the form "[n] Authors. (year). Title. Venue...".
  3. Pulls DOIs from the entry text. For entries without one, asks Crossref and
     accepts a match only if the title is at least 90% similar. Results are
     cached in tools/doi_cache.json so reruns are fast and stable.
  4. Rewrites only the region between <!-- PUBS:START --> and <!-- PUBS:END -->
     in publications.html. Everything else on the page is left alone.

"Manuscripts Under Review" are skipped on purpose.
Selected papers are chosen by CV number in SELECTED below.
"""
import difflib
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "publications.html"
CACHE = ROOT / "tools" / "doi_cache.json"

# Selected papers, shown first, grouped. Keys are CV article numbers.
SELECTED = [
    ("Where it started", [17, 13, 10]),
    ("Stress and resilience", [77, 52]),
    ("Neighborhood and community", [71, 70]),
    ("Aging and biology", [63]),
    ("Methods and open science", [60, 38]),
]

# DOIs checked by hand (2026-09-26) where Crossref's title match fell below 0.9.
# Each was confirmed against the journal and article number/title in the CV.
DOI_OVERRIDES = {
    78: "10.1002/hbm.70458",               # HBM 2026, same title
    54: "10.1016/j.neubiorev.2023.105450",  # Neurosci Biobehav Rev, article 105450
    50: "10.1111/jcpp.13793",              # JCPP 2023; published title says "stress across adolescence"
    48: "10.1016/j.eclinm.2022.101784",    # eClinicalMedicine 56, 101784
    47: "10.1038/s41597-022-01695-7",      # Scientific Data 9, 616
}

SECTIONS = [
    ("articles", "Peer-Reviewed Journal Articles:"),
    ("chapters", "Book Chapters:"),
    ("commentaries", "Journal Commentaries:"),
]
STOP = "Manuscripts Under Review"

ENTRY_RE = re.compile(r"^\[(\d+)\]\s*(.+)$")
YEAR_RE = re.compile(r"^(.*?)\.?\s*\((\d{4})[^)]*\)\.?\s*(.*)$")
STATUS_RE = re.compile(r"^(.*?)\.?\s*\((accepted|in press)\)\.?\s*(.*)$", re.I)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,;]+")
PREPRINT_RE = re.compile(r"Preprint available at:\s*(\S+)", re.I)
ME_RE = re.compile(r"Hanson,?\s*J\.?\s*(?:L\.?)?(?=[\s,.;)*#†]|$)")


def read_cv(path):
    path = Path(path)
    if path.suffix.lower() in (".docx", ".doc", ".rtf"):
        out = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)],
                             check=True, capture_output=True, text=True)
        return out.stdout
    return path.read_text()


def split_sections(text):
    lines = [l.strip() for l in text.splitlines()]
    found = {}
    current = None
    for line in lines:
        if line.startswith(STOP):
            current = None
            continue
        for key, heading in SECTIONS:
            if line.startswith(heading):
                current = key
                found.setdefault(key, [])
                break
        else:
            if current and ENTRY_RE.match(line):
                found[current].append(line)
    return found


def parse_entry(line):
    num, body = ENTRY_RE.match(line).groups()
    num = int(num)
    status = None
    m = STATUS_RE.match(body)
    if m:
        authors, status, rest = m.groups()
        year = None
        status = status.lower()
    else:
        m = YEAR_RE.match(body)
        if m:
            authors, year, rest = m.groups()
            year = int(year)
        else:
            # No year in the entry (e.g. "[40] ... Pollak SD. Title. Journal").
            # Split authors from the rest at the first ". " after an initial.
            m = re.search(r"\b[A-Z]{1,2}[#*†]*\.\s+(?=[A-Z])", body)
            authors, rest = (body[:m.end()], body[m.end():]) if m else (body, "")
            year = None

    preprint = PREPRINT_RE.search(rest)
    preprint = preprint.group(1).rstrip(".") if preprint else None
    # Look for the article DOI only outside the preprint link.
    doi = DOI_RE.search(PREPRINT_RE.sub("", rest))
    doi = doi.group(0).rstrip(".") if doi else None
    rest = re.sub(r"(\w)\. (io|org|com)\b", r"\1.\2", rest)  # "brainlife. io" -> "brainlife.io"

    # Strip links and "doi:" noise from the citation text.
    clean = PREPRINT_RE.sub("", rest)
    clean = re.sub(r"(doi:?\s*)?(https?://)?(dx\.)?(doi\.org/)?10\.\d[\S]*", "", clean, flags=re.I)
    clean = re.sub(r"https?://\S+", "", clean)
    clean = re.sub(r"\bdoi:?\s*$", "", clean.strip(), flags=re.I).strip(" .,")

    # Title ends at the first ". " or "? " boundary.
    m = re.match(r"^(.+?[.?!])\s+(?=[A-Z0-9\"“])(.*)$", clean)
    title, venue = (m.group(1), m.group(2)) if m else (clean, "")
    title = title.rstrip(".")
    return {
        "num": num, "authors": authors.strip().rstrip("."), "year": year,
        "status": status, "title": title.strip(), "venue": venue.strip(" .,"),
        "doi": doi, "preprint": preprint,
    }


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower())


# Preprint servers (bioRxiv/medRxiv, PsyArXiv/OSF): never use these as the article DOI.
PREPRINT_DOI_PREFIXES = ("10.1101/", "10.31234/", "10.31219/", "10.21203/")


def fetch_json(url, tries=4):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                time.sleep(5 * (attempt + 1))  # Crossref rate limit: back off
                continue
            raise


def crossref_lookup(entry, cache):
    key = f"{entry['num']}|{norm(entry['title'])[:80]}"
    if cache.get(key):  # only hits are cached; misses are retried next run
        return cache[key]
    q = urllib.parse.urlencode({
        "query.bibliographic": f"{entry['title']} {entry['venue']}",
        "rows": 5,
        "select": "DOI,title,issued",
        "mailto": "jamhanson@mcw.edu",
    })
    result = None
    try:
        time.sleep(1)  # be polite to Crossref
        items = fetch_json(f"https://api.crossref.org/works?{q}")["message"]["items"]
        items = [it for it in items if not it["DOI"].startswith(PREPRINT_DOI_PREFIXES)]
        for it in items:
            cand = (it.get("title") or [""])[0]
            score = difflib.SequenceMatcher(None, norm(cand), norm(entry["title"])).ratio()
            if score >= 0.9:
                year = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
                result = {"doi": it["DOI"], "year": year, "score": round(score, 3)}
                break
    except Exception as e:  # network off: leave it missing, report it
        print(f"  crossref failed for [{entry['num']}]: {e}", file=sys.stderr)
        return None
    if result:
        cache[key] = result
    return result


def fmt_authors(a):
    a = html.escape(a)
    a = ME_RE.sub(lambda m: f'<span class="me">{m.group(0)}</span>', a)
    return a


def render_entry(e, kind):
    links = []
    if e["doi"]:
        links.append(f'<li><a href="https://doi.org/{html.escape(e["doi"])}">DOI<span class="visually-hidden">: {html.escape(e["title"])}</span></a></li>')
    if e["preprint"]:
        links.append(f'<li><a href="{html.escape(e["preprint"])}">Preprint<span class="visually-hidden">: {html.escape(e["title"])}</span></a></li>')
    links_html = f'\n                <ul class="pub-links">{"".join(links)}</ul>' if links else ""
    when = e["status"].title() if e["status"] else (str(e["year"]) if e["year"] else "")
    venue = html.escape(e["venue"])
    # Italicize the journal/book name: text before the first comma.
    if venue and kind == "articles":
        head, sep, tail = venue.partition(",")
        venue = f"<cite>{head}</cite>{sep}{tail}"
    return f"""              <li class="pub">
                <p class="pub-authors">{fmt_authors(e["authors"])}</p>
                <p class="pub-title">{html.escape(e["title"])}</p>
                <p class="pub-venue">{venue}{". " if venue else ""}{when}.</p>{links_html}
              </li>"""


def build(cv_path):
    sections = split_sections(read_cv(cv_path))
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    data = {}
    for key, _ in SECTIONS:
        entries = [parse_entry(l) for l in sections.get(key, [])]
        for e in entries:
            if key == "articles" and e["num"] in DOI_OVERRIDES:
                e["doi"] = e["doi"] or DOI_OVERRIDES[e["num"]]
            if key == "articles" and (not e["doi"] or (not e["year"] and not e["status"])):
                hit = crossref_lookup(e, cache)
                if hit:
                    e["doi"] = e["doi"] or hit["doi"]
                    if not e["status"]:
                        e["year"] = e["year"] or hit["year"]
        data[key] = entries
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))

    arts = {e["num"]: e for e in data["articles"]}
    missing_sel = [n for _, nums in SELECTED for n in nums if n not in arts]
    if missing_sel:
        sys.exit(f"Selected paper numbers not in CV: {missing_sel}")

    out = []
    out.append('        <section class="pub-selected" aria-labelledby="selected-title">')
    out.append('          <h2 id="selected-title">Selected papers</h2>')
    for label, nums in SELECTED:
        out.append(f'          <h3 class="pub-group">{html.escape(label)}</h3>')
        out.append('          <ul class="pub-list">')
        out += [render_entry(arts[n], "articles") for n in nums]
        out.append("          </ul>")
    out.append("        </section>")

    # Full list, grouped: in press first, then by year, then chapters and commentaries.
    groups = {}
    for e in data["articles"]:
        g = "In press" if e["status"] or not e["year"] else str(e["year"])
        groups.setdefault(g, []).append(e)
    order = (["In press"] if "In press" in groups else []) + sorted(
        (g for g in groups if g != "In press"), key=int, reverse=True)
    total = sum(len(v) for v in data.values())

    jump = " ".join(f'<a href="#y-{g.replace(" ", "-").lower()}">{g}</a>' for g in order)
    extra = []
    if data.get("chapters"):
        extra.append('<a href="#y-chapters">Chapters</a>')
    if data.get("commentaries"):
        extra.append('<a href="#y-commentaries">Commentaries</a>')

    out.append('        <details class="pub-all" id="all">')
    out.append(f'          <summary>All publications ({total})</summary>')
    out.append(f'          <nav class="pub-jump" aria-label="Jump to year">{jump} {" ".join(extra)}</nav>')
    for g in order:
        gid = f'y-{g.replace(" ", "-").lower()}'
        out.append(f'          <section class="pub-year" aria-labelledby="{gid}">')
        out.append(f'            <h2 id="{gid}">{g}</h2>')
        out.append('            <ol class="pub-list">')
        out += ["  " + r for r in (render_entry(e, "articles") for e in groups[g])]
        out.append("            </ol>")
        out.append("          </section>")
    for key, label in (("chapters", "Book chapters"), ("commentaries", "Commentaries")):
        if data.get(key):
            out.append(f'          <section class="pub-year" aria-labelledby="y-{key}">')
            out.append(f'            <h2 id="y-{key}">{label}</h2>')
            out.append('            <ol class="pub-list">')
            out += ["  " + render_entry(e, key) for e in data[key]]
            out.append("            </ol>")
            out.append("          </section>")
    out.append("        </details>")

    page = PAGE.read_text()
    start, end = "<!-- PUBS:START -->", "<!-- PUBS:END -->"
    if start not in page or end not in page:
        sys.exit("publications.html is missing the PUBS:START / PUBS:END markers")
    before, rest = page.split(start, 1)
    _, after = rest.split(end, 1)
    PAGE.write_text(before + start + "\n" + "\n".join(out) + "\n        " + end + after)

    no_doi = [e["num"] for e in data["articles"] if not e["doi"] and not e["preprint"]]
    print(f"articles={len(data['articles'])} chapters={len(data.get('chapters', []))} "
          f"commentaries={len(data.get('commentaries', []))} total={total}")
    print(f"articles without a DOI or preprint link: {no_doi or 'none'}")
    return data


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(sys.argv[1])
