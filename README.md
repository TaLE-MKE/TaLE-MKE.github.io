# TaLE MKE website

Static site for **TaLE MKE: Trajectories and Lifespan Experience in Milwaukee** (PI: Jamie Hanson, Department of Pediatrics, Medical College of Wisconsin and Children's Wisconsin).

Plain HTML, CSS, and a small vanilla JS file. No framework, no build step. The only external dependency is Google Fonts (Source Serif 4 and Source Sans 3).

## Files

```
index.html          Home: hero, affiliations, "what we do" cards
research.html       Mission, 4 focus areas, PI bio
team.html           PI card + 6 member placeholder cards
publications.html   Reverse-chronological list grouped by year
news.html           3 dated news entries
contact.html        Contact info, contact form, open positions
css/styles.css      All styles; brand colors at the top in :root
js/main.js          Mobile nav, footer year, contact form validation
assets/img/         logo-horizontal.webp (header), logo-square.webp (footer),
                    logo-mark.svg (favicon), photo placeholders
assets/img/brand/   Full-resolution logo PNGs (print, slides, social)
tests/check_site.py Static checks (links, alt text, nav, labels, contrast)
```

## Preview locally

Open `index.html` in a browser, or run a local server (better, since it matches how the site is hosted):

```bash
python3 -m http.server 8000
```

Then visit http://localhost:8000.

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

## Replace the placeholders

Every spot is marked with an HTML/CSS comment containing `PLACEHOLDER`. List them all with:

```bash
grep -rn PLACEHOLDER --include=*.html --include=*.css --include=*.svg .
```

Visible placeholder text is in `[square brackets]`.

| What | Where |
|---|---|
| Lab email (`your-email@mcw.edu`) | Footer of all 6 pages, and 2 places in `contact.html` |
| Building / address | Footer of all 6 pages, and `contact.html` |
| One-line mission | `index.html` hero, `research.html` mission block |
| "What we do" summary | `index.html` |
| Expanded mission (2 paragraphs) | `research.html` |
| 4 focus areas (heading + paragraph each) | `research.html`. Delete a card if you only want 2 or 3. |
| PI bio, degree ("PhD"), CV link | `research.html`; degree also on `team.html` |
| PI headshot | `research.html` and `team.html`: point `src` at e.g. `assets/img/hanson.jpg` and update `alt` |
| Lab group photo | `index.html` hero |
| 6 lab member cards (photo, name, role, bio) | `team.html`. Copy/delete `<article class="card person-card">` blocks to change the count. |
| Publications (authors, title, journal, DOI, PDF) | `publications.html`. Add a new `<section class="pub-year">` per year. |
| Google Scholar / PubMed links | `publications.html` note box |
| 3 news items | `news.html`. Update both the `datetime` attribute and the visible date. |
| Recruiting blurb and 3 open positions | `contact.html` |
| Contact form handler | `js/main.js` `FORM_ENDPOINT`, and `action=""` on the form in `contact.html` (see below) |

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

The form is front end only. It validates input and, until connected, tells the visitor to email instead. To receive messages with Formspree:

1. Create a form at https://formspree.io and copy the endpoint (`https://formspree.io/f/xxxxxxx`).
2. Paste it into `FORM_ENDPOINT` near the top of the form section in `js/main.js`.
3. Paste the same URL into `action=""` on `<form id="contact-form">` in `contact.html`.

### Photos

Use JPG or WebP. Suggested sizes: headshots square, 600x600 or larger; lab photo 4:3, 1200x900 or larger. Always write an `alt` that describes the person or scene.

### Editing the shared header and footer

The header and footer are repeated in each of the 6 HTML files (no build step). When you change one, change all six. `tests/check_site.py` catches nav drift.
