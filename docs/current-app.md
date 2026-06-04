# Current Application: verfassungsschutzberichte.de

Reference documentation for the existing Flask application, to guide the Next.js migration.

> **Migration note**: In the new app, "Blog" is renamed to "News" (`/blog` → `/news`). See `docs/migration-overview.md` for the full migration plan and `docs/design.md` for the "Aufklärung" design system.

## Overview

An open-source civic tech archive that collects, digitizes, and makes searchable all German constitutional protection reports (Verfassungsschutzberichte) from federal and state authorities. Enables researchers, journalists, and activists to analyze how the Verfassungsschutz monitors political movements.

- **Framework**: Flask 3.1.3 + Jinja2
- **Database**: PostgreSQL 11 with SQLAlchemy + SQLAlchemy-Searchable (TSVector full-text search)
- **Cache**: Redis (production) / Null (development)
- **Frontend**: Bootstrap 5, Chart.js v2, jQuery, lazysizes.js
- **Deployment**: Docker + Dokku (Gunicorn behind nginx)
- **Source**: `src/app.py` (single file, ~1189 lines)

## Database Schema

Three SQLAlchemy models, all in `src/app.py`:

### Document (lines 77-83)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | |
| year | Integer | Report year |
| title | String | e.g. "Verfassungsschutzbericht 2023" |
| jurisdiction | String | Title-cased (e.g. "Bund", "Bayern", "Nordrhein-Westfalen") |
| file_url | String (unique) | e.g. "/pdfs/vsbericht-bfv-2023.pdf" |
| num_pages | Integer | |

### DocumentPage (lines 86-99)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | |
| document_id | Integer (FK -> document.id) | |
| page_number | Integer | 1-based |
| content | UnicodeText | Cleaned page text |
| file_url | String (unique) | e.g. "/images/vsbericht-bfv-2023_0.jpg" |
| search_vector | TSVectorType | Auto-populated from `content`, German config |

Uses `DocumentQuery(Query, SearchQueryMixin)` for full-text search via `sqlalchemy_searchable`.

### TokenCount (lines 102-109)
| Column | Type | Notes |
|--------|------|-------|
| id | Integer (PK) | |
| document_id | Integer (FK -> document.id) | |
| token | String | Lowercased token |
| count | Integer | Frequency in document |

Used for trend analysis and autocomplete.

## Full-Text Search

**Config**: `pg_catalog.german` for TSVector and ts_headline.

**Search flow** (`/suche` route, lines 866-933):
1. Clean query with `cleantext.clean(q, lang="de")`
2. Build query with optional filters (jurisdiction, min_year, max_year)
3. `DocumentPage.query.search(q, sort=True)` - uses SQLAlchemy-Searchable which calls `parse_websearch()` -> `to_tsquery()`
4. Paginate (20 per page)
5. Generate snippets via raw SQL:
   ```sql
   ts_headline('pg_catalog.german', content,
     websearch_to_tsquery('pg_catalog.german', :q),
     'MaxFragments=10, MinWords=5, MaxWords=20, FragmentDelimiter=XXX.....XXX')
   ```
6. Split snippets on `XXX.....XXX` delimiter
7. Load word position JSON from `/data/wordpos/` for highlight boxes
8. Match search tokens against word bounding boxes (up to 50 boxes per page)

**Search syntax** (PostgreSQL websearch_to_tsquery):
- Phrases: `"kommunistische partei"` (quotes)
- OR: `links OR rechts`
- Negation: `-extremistisch`
- Parentheses: `(links OR rechts) kind`
- All matches are prefix-based automatically

## Routes (20 total)

### Public Pages
| Route | Function | Cache | Template |
|-------|----------|-------|----------|
| `GET /` | `index()` | 1h | `index.html` |
| `GET /berichte` | `reports()` | 1h | `reports.html` |
| `GET /<jurisdiction>/<year>` | `details()` | 1h | `details.html` |
| `GET /suche` | `search()` | query_string | `search.html` |
| `GET /trends` | `trends()` | query_string | `trends.html` |
| `GET /regional` | `regional()` | query_string | `regional.html` |
| `GET /impressum` | `impressum()` | 1h | `impressum.html` |
| `GET /blog/` | `blog_index()` | 30m | `blog_index.html` |
| `GET /blog/<slug>` | `blog_post()` | 30m | `blog_post.html` |

### File Serving
| Route | Function | Notes |
|-------|----------|-------|
| `GET /pdfs/<filename>` | `download_pdf()` | X-Accel-Redirect in prod, send_from_directory in debug |
| `GET /images/<filename>` | `download_img()` | AVIF/JPEG content-type detection |
| `GET /downloads/<filename>` | `download_file()` | Whitelist: vsberichte.zip, vsberichte-texts.zip |
| `GET /blog/images/<filename>` | `blog_image()` | Serve from /app/blog/images/ |
| `GET /robots.txt` | `static_from_root()` | |

### API Endpoints (JSON)
| Route | Function | Response |
|-------|----------|----------|
| `GET /api` | `api_index()` | `{reports: [{jurisdiction, years, jurisdiction_escaped}], total}` |
| `GET /api/<jurisdiction>/<year>` | `api_details()` | `{year, title, jurisdiction, file_url, num_pages, pages: [text...]}` |
| `GET /api/auto-complete?q=` | `api_search_auto()` | `["token1", "token2", ...]` (up to 10) |
| `GET /api/mentions?q=` | `api_mentions()` | JSON matrix or CSV (`?csv=1`) |
| `GET /stats?q=` | `stats()` | `["query", {year: relative_frequency, ...}]` |

### Text Export
| Route | Function | Notes |
|-------|----------|-------|
| `GET /<jurisdiction>-<year>.txt` | `text_details()` | All pages concatenated, Content-Type: text/plain |

## CLI Commands

All defined in `src/app.py` via `@app.cli.command()`:

| Command | Arguments | Description |
|---------|-----------|-------------|
| `flask init-db` | | Create database tables |
| `flask clear-cache` | | Flush Redis cache |
| `flask update-docs <pattern>` | glob pattern (e.g. `'*'`) | Process PDFs: extract text, tokenize, generate images, extract word positions |
| `flask remove-docs <pattern>` | filename | Delete document + cascading pages/tokens |
| `flask clear-data` | | Drop all tables, reimport all PDFs |
| `flask generate-images <pattern>` | `--force` | Regenerate JPEG+AVIF page images |
| `flask extract-wordpos <pattern>` | `--force` | Extract word bounding boxes from PDFs |
| `flask create-zips` | `--force`, `--pdfs/--no-pdfs`, `--texts/--no-texts` | Build vsberichte.zip and vsberichte-texts.zip |
| `flask export-data <output>` | tar path | Export all PDF directories as tar |
| `flask import-data <input>` | tar path | Import PDFs from tar |

## PDF Processing Pipeline (`proc_pdf()`, lines 251-327)

1. Parse jurisdiction from filename: `vsbericht-bw-2023.pdf` -> `Baden-Wurttemberg`
2. Parse year from filename
3. Create `Document` record
4. Convert PDF to images with `pdf2image` (batch, faster than per-page)
5. Extract text per page with `pdftotext`, clean with `cleantext`
6. Save images in parallel (ThreadPoolExecutor) as JPEG (900px) + AVIF (quality=50)
7. Create `DocumentPage` records with cleaned text
8. Tokenize text with spaCy German tokenizer, create `TokenCount` records
9. Extract word positions with `pdfplumber` -> gzipped JSON in `/data/wordpos/`

## Data Directory Structure

```
/data/
  pdfs/           # Raw PDF files (source)
  images/         # Generated JPEG + AVIF page thumbnails (900px)
  wordpos/        # Gzipped JSON word bounding boxes (per page)
  zips/           # vsberichte.zip, vsberichte-texts.zip
  cleaned/        # Processed PDFs (export/import)
  raw/            # Original PDFs (export/import)
  deleted/        # Removed PDFs archive
```

## Templates (10 files in `src/templates/`)

| Template | Purpose | Key Features |
|----------|---------|-------------|
| `base.html` | Root layout | Nav, footer, newsletter (Listmonk), Matomo analytics, security headers |
| `index.html` | Homepage | 4 Chart.js graphs (RAF/NSU, parties, media, cyber), stats, FAQ |
| `reports.html` | Reports grid | Jurisdiction-grouped year buttons, color-coded (available/missing/not-published) |
| `details.html` | Document viewer | All pages as lazy-loaded JPEG/AVIF images, word count, download links |
| `search.html` | Search | Filters, paginated results with snippets + highlight boxes over page images |
| `trends.html` | Trend comparison | Multi-term Chart.js line chart, token management, export (JPG/CSV) |
| `regional.html` | Regional heatmap | Chart.js matrix chart, mentions by jurisdiction x year |
| `blog_index.html` | Blog listing | Posts sorted by date, truncated to 300 chars |
| `blog_post.html` | Blog post | Rendered markdown with responsive tables |
| `impressum.html` | Legal page | Contact, imprint |

**Navbar** is duplicated in each template (not extracted into a partial).

## Static Assets

### JavaScript
- `scripts.js` - `drawLineChart()` function (shared by homepage, search, trends), polyfills
- `lib/bootstrap.min.js`, `lib/popper.min.js` - Bootstrap 5
- `lib/jquery.min.js` - jQuery (used for autocomplete + Bootstrap)
- `lib/Chart.min.js` + `chartjs-chart-matrix.min.js` - Chart.js v2
- `lib/bootstrap-autocomplete.min.js` - Search autocomplete
- `lib/lazysizes.min.js` - Lazy image loading
- `lib/FileSaver.min.js` - Client-side file saving (chart export)
- `lib/unfetch.js`, `lib/es6-promise.auto.min.js` - Polyfills (no longer needed)

### CSS
- `lib/bootstrap.min.css` - Bootstrap 5 (~160KB)
- `lib/Chart.min.css` - Chart.js
- `styles.css` - Custom: 75 lines (anchor offsets, search highlight, hyphenation)

## External Services

- **Matomo** analytics at `matomo.daten.cool` (site ID: 3)
- **Listmonk** newsletter at `listen.daten.cool` (form action set via JS to avoid bots)
- **Tor/Onion service**: `zq5xve7vxljrsccptc4wxmuebnuiglhylahfwahyw7dzlxc43em4w6yd.onion`

## Security Headers (set via `@app.after_request`)

- `Cache-Control: public, max-age=604800` (1 week, all responses)
- `Strict-Transport-Security: max-age=31536000; includeSubdomains; preload`
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' matomo.daten.cool; ...`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin`
- `Onion-Location: <onion URL>`
- `X-Robots-Tag: noindex, nofollow` (on search results, files, stats)

## Deployment

- **Dockerfile**: Python 3.10, system deps for poppler + libavif, pip install requirements
- **Procfile**: `web: gunicorn app:app`
- **Dokku**: PostgreSQL + Redis linked, `/data` mounted at `/mnt/vsb`
- **nginx**: X-Accel-Redirect for `/internal-pdfs/`, `/internal-images/`, `/internal-zips/`

## Report Metadata (`src/report_info.py`)

Static metadata for jurisdictions:
- **Abbreviations**: 16 German states (BW, BY, BE, BB, HB, HH, HE, MV, NI, NW, RP, SL, SN, ST, SH, TH)
- **Start years**: When each jurisdiction began publishing (1950 NRW - 2013 Saarland)
- **No reports**: Years when a jurisdiction didn't publish
- **Title overrides**: Reports spanning multiple years (e.g. "1992/1993")
- **Changes**: Legal challenges to reports (Bayern 2019)
- **Comments**: Annotations (Sachsen-Anhalt 2012 anonymization)

## Known Issues / Tech Debt

- Navbar duplicated across all templates
- Heavy inline styles (newsletter, footer)
- `user-scalable=0` in viewport meta (accessibility violation)
- jQuery + polyfills loaded globally but barely used
- Chart.js v2 (outdated, v4 available)
- Bootstrap 5 loaded in full (~160KB) but few features used
- `time.sleep(10)` on debug startup (waiting for DB)
- No cascade on Document FK (manual deletion workaround in `remove_docs`)
- CSP uses `unsafe-inline` and `unsafe-eval`
