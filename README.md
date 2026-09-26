# TaLE MKE website

Static site for **TaLE MKE: Trajectories and Lifespan Experience in Milwaukee** (PI: Jamie Hanson, Department of Pediatrics, Medical College of Wisconsin and Children's Wisconsin).

Plain HTML, CSS, and a small vanilla JS file. No framework, no build step. The only external dependency is Google Fonts (Source Serif 4 and Source Sans 3).

## Files

```
index.html          Home: tagline, affiliations, six section cards
research.html       Mission, 4 focus areas, PI bio and headshot
team.html           PI, lab alumni with current positions, collaborators
publications.html   10 selected papers + all 92 (generated from the CV)
participate.html    For families: what studies involve, privacy, how to reach us
news.html           Dated news items
funding.html        Current and recent grants (footer + Research link, not in nav)
contact.html        Contact info, message form, how to join the lab
css/styles.css      All styles; brand colors at the top in :root
js/main.js          Mobile nav, footer year, contact form validation
assets/img/         logo-horizontal.webp (header), logo-square.webp (footer),
                    logo-mark.svg (favicon), photo placeholders
assets/img/brand/   Full-resolution logo PNGs (print, slides, social)
tests/check_site.py Static checks (links, alt text, nav, labels, contrast, pubs)
tools/update_publications.py   Rebuilds the publication list from the CV
tools/doi_cache.json           Crossref DOI matches (keeps reruns fast and stable)
```

## Preview locally

Open `index.html` in a browser, or run a local server (better, since it matches how the site is hosted):

```bash
python3 -m http.server 8000
```

Then visit http://localhost:8000.

## Update publications from your CV

```bash
python3 tools/update_publications.py ~/Library/CloudStorage/Dropbox/CV_Resume_mostUptoDate/Hanson_CV_YYYYMMDD.docx
```

Reads the "Peer-Reviewed Journal Articles", "Book Chapters", and "Journal Commentaries" sections (skips "Manuscripts Under Review"), fills missing DOIs from Crossref (only title matches of 90% or better, never preprint-server DOIs), and rewrites only the block between `<!-- PUBS:START -->` and `<!-- PUBS:END -->` in `publications.html`. To change the selected papers or their group labels, edit `SELECTED` at the top of the script. DOIs checked by hand live in `DOI_OVERRIDES`. The script prints any article still missing a link.

## Check before publishing

```bash
python3 tests/check_site.py
```

Fails on: broken local links or anchors, images without `alt`, pages without exactly one `<h1>`, nav that differs across pages, form fields without labels, external assets other than Google Fonts, em dashes, and any brand color pair below WCAG AA (4.5:1). It also prints how many `PLACEHOLDER` markers remain. Rerun it after changing colors.

## Deploy

**GitHub Pages**
1. Create a repo on GitHub and push this folder to `main`.
2. Repo Settings > Pages > Source: "Deploy from a branch", branch `main`, folder `/ (root)`.
3. The site appears at `https://<user>.github.io/<repo>/` within a minute or two.

**Vercel or Netlify**
Import the repo, choose "Other" / no framework, leave the build command empty, output directory `.`.

## What still needs you

| What | Where |
|---|---|
| Lab group photo | `index.html` hero (the only `PLACEHOLDER` left). Swap `src` and `alt`. |
| Form handler | The contact form is front end only. See "Wiring the contact form" below. |
| Payment wording on Participate | `participate.html`, marked `CONFIRM`. It says studies "often include payment"; confirm before launch. |

### Brand colors and logo

Colors are sampled from the TaLE MKE logo and live at the top of `css/styles.css`:

| Token | Hex | Used for |
|---|---|---|
| `--color-primary` | `#0074c8` | Logo blue: header, home hero, footer, buttons, links |
| `--color-primary-dark` | `#005a9c` | Hover states; blue text on pale-blue surfaces |
| `--color-secondary` | `#007065` | Logo green: trajectory line, focus-area accents |
| `--color-accent-light` | `#7eb8e0` | Logo light-blue lines |
| `--color-accent-pale` | `#c1ddf4` | Logo pale-blue lines |

The header and footer background must stay exactly `#0074c8` so the logo images blend in. If the logo is ever re-exported in another color, change `--color-primary` to match. The favicon and placeholder SVGs use the same hex values. Logo blue on white is 4.85:1 (passes AA); logo blue on pale blue does not, so text on pale-blue surfaces uses `--color-primary-dark`. `tests/check_site.py` enforces this.

### Wiring the contact form

The message form on `contact.html` is front end only. It validates input and, until connected, tells the visitor to email instead. To receive messages with Formspree:

1. Create a form at https://formspree.io and copy the endpoint (`https://formspree.io/f/xxxxxxx`).
2. Paste it into `FORM_ENDPOINT` near the top of the form section in `js/main.js`.
3. Paste the same URL into `action=""` on `<form id="contact-form">` in `contact.html`.

The validation code handles any `<form class="js-form">`, so a family sign-up form can be added to `participate.html` later without new JavaScript. Before collecting families' contact details, check with MCW/Children's Wisconsin research compliance about where that data may be stored (they may require REDCap).

### Photos

Use JPG or WebP. Suggested sizes: headshots square, 600x600 or larger; lab photo 4:3, 1200x900 or larger. Always write an `alt` that describes the person or scene.

### Editing the shared header and footer

The header and footer are repeated in each of the 8 HTML files (no build step). When you change one, change all eight. `tests/check_site.py` catches nav drift.
