# Migration Overview: Flask to Next.js 16

## Why Migrate

### Current Limitations
- **No CMS**: Content (news posts, static pages) is managed via markdown files in the repo. Only developers can add or edit content.
- **No contributor workflow**: Community members can't contribute content, suggest corrections, or help curate the archive without code access.
- **Monolithic single file**: All 1189 lines of routes, models, CLI commands, and PDF processing live in one `app.py`.
- **Outdated frontend**: Bootstrap 5 loaded in full (~160KB), Chart.js v2, jQuery, unnecessary polyfills. No dark mode.
- **No static generation**: Every page is rendered on every request (cached in Redis for 1 hour). Report pages rarely change but are still dynamically rendered.
- **Limited design flexibility**: Jinja2 templates with duplicated navbar, heavy inline styles, no component system.

### Goals
- **Payload CMS** for content management (news, pages) with admin UI and contributor roles
- **Static generation** for content pages that rarely change (reports, document viewer, homepage)
- **Server-side rendering** for search/analysis pages that must work without JavaScript
- **Modern design** with dark mode, accessibility (WCAG AA), mobile-first
- **Community contributions** via CMS editor roles (admin/editor/contributor)
- **Future extensibility** for document types beyond Verfassungsschutzberichte

## Tech Stack

| Layer | Current | New | Rationale |
|-------|---------|-----|-----------|
| Framework | Flask 3.1 | Next.js 16 App Router | Static + SSR hybrid, React ecosystem |
| CMS | None (markdown files) | Payload CMS v3 | Admin UI, auth, roles, rich text editor |
| Language | Python | TypeScript | Type safety, same language frontend/backend |
| CSS | Bootstrap 5 (CDN, 160KB) | Tailwind CSS v4 | Utility-first, dark mode, smaller bundle |
| Charts | Chart.js v2 | Chart.js v4 | Tree-shaking, better a11y, dark mode |
| Database | PostgreSQL + SQLAlchemy | PostgreSQL + Drizzle (Payload) + raw SQL | Single DB, Payload manages CMS tables |
| Cache | Redis | Next.js ISR + data cache | Built-in, no extra service |
| Search | SQLAlchemy-Searchable | Raw SQL (TSVector, ts_headline) | Direct PostgreSQL, no ORM abstraction |
| PDF Processing | Python CLI (Flask commands) | Python CLI (unchanged) | No Node.js equivalents for pdftotext, pdfplumber, spaCy |
| Rich Text | Markdown (python-markdown) | Lexical (Payload built-in) | WYSIWYG editor for non-technical contributors |
| Deployment | Docker + Dokku + Gunicorn | Docker + Dokku + Node standalone | Same infra |
| Analytics | Matomo | Matomo | Unchanged |

## What Stays

- **PostgreSQL database** with existing tables (document, document_page, token_count)
- **Python CLI tools** for PDF processing (update-docs, generate-images, extract-wordpos, create-zips, export/import)
- **Full-text search** via PostgreSQL TSVector with German config
- **Data directory** structure (`/data/pdfs`, `/data/images`, `/data/wordpos`, `/data/zips`)
- **All existing URLs** preserved (same route patterns)
- **External services**: Matomo analytics, Listmonk newsletter, Tor onion service
- **Dokku deployment** with mounted data volume

## What Changes

- **Frontend**: React components with Tailwind CSS instead of Jinja2 + Bootstrap
- **CMS**: Payload CMS admin UI at `/admin` for news posts, pages, and media
- **Rendering**: Static generation (ISR) for content pages, SSR for search/analysis
- **Cache**: Next.js built-in caching replaces Redis (one fewer service to manage)
- **Design**: "Aufklärung" editorial design (see `docs/design.md` and `docs/prototypes/`), dark mode, accessibility improvements
- **News**: From markdown blog posts to Payload CMS rich text (Lexical editor), renamed from "Blog" to "News"
- **Auth**: Payload user system with roles (admin/editor/contributor)

## Phased Approach

### Phase 1: Homepage + Design System
Set up Next.js + Payload + Tailwind. Build the landing page using the "Aufklärung" (editorial) design from `docs/prototypes/variant-b-aufklaerung.html`. Design system documented in `docs/design.md`.

### Phase 2: Reports + Document Viewer
Static generation for `/berichte` grid and `/[jurisdiction]/[year]` document viewer. File serving for PDFs and images.

### Phase 3: Search
Server-rendered search at `/suche` with full-text search, snippets, highlight boxes, pagination. Must work without JavaScript.

### Phase 4: API Routes
Port all JSON endpoints: `/api`, `/api/<jurisdiction>/<year>`, `/api/auto-complete`, `/api/mentions`, `/stats`.

### Phase 5: Analysis Pages
`/trends` and `/regional` with Chart.js v4 client components. No-JS fallback: server-rendered data tables.

### Phase 6: CMS Content
Payload collections for news articles and static pages. Migrate existing 4 blog posts as news articles. Access control for community contributors.

### Phase 7: Polish + Deploy
Security headers, robots.txt, Matomo, newsletter, Onion-Location, Dockerfile, Dokku deployment.

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Search parity | Integration tests comparing Flask and Next.js search results for same queries |
| URL breakage | Preserve all existing URL patterns exactly |
| Build-time DB | Use ISR (revalidate) instead of generateStaticParams if DB not available at build |
| PDF CLI dependency | Keep Python CLI as separate container, shares same PostgreSQL + /data volume |
| Payload + custom tables | Payload uses Drizzle for its own tables; custom search tables can coexist in same DB or use raw SQL |
