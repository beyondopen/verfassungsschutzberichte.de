# Architecture: Next.js 16 + Payload CMS

## Overview

The new application is a single Next.js 16 process that embeds Payload CMS v3. It connects to a single PostgreSQL database that holds both Payload's CMS tables (managed via Drizzle ORM) and the existing search tables (document, document_page, token_count) managed by the Python CLI.

```
                    ┌──────────────────────────────────┐
                    │       Next.js 16 App Router       │
                    │                                    │
                    │  ┌────────────┐  ┌──────────────┐ │
                    │  │  Frontend  │  │ Payload CMS  │ │
                    │  │  Pages     │  │ Admin UI     │ │
                    │  │  (React)   │  │ (/admin)     │ │
                    │  └─────┬──────┘  └──────┬───────┘ │
                    │        │                │          │
                    │  ┌─────┴────────────────┴───────┐ │
                    │  │        PostgreSQL              │ │
                    │  │  Payload tables  │ Search tbls │ │
                    │  │  (Drizzle ORM)  │ (raw SQL)   │ │
                    │  └──────────────────────────────┘ │
                    └──────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────────┐
                    │         /data/ (mounted volume)    │
                    │   pdfs/ images/ wordpos/ zips/     │
                    └───────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────────┐
                    │     Python CLI (separate container) │
                    │  update-docs, generate-images, etc. │
                    └───────────────────────────────────┘
```

## Project Structure

```
vsberichte-next/
├── app/
│   ├── (frontend)/                         # Route group: public-facing pages
│   │   ├── layout.tsx                      # Nav, footer, Matomo, skip-to-content
│   │   ├── page.tsx                        # Homepage (/)
│   │   ├── berichte/page.tsx               # Reports grid
│   │   ├── [jurisdiction]/[year]/page.tsx  # Document viewer
│   │   ├── suche/page.tsx                  # Search (SSR)
│   │   ├── trends/page.tsx                 # Trends (SSR)
│   │   ├── regional/page.tsx               # Regional (SSR)
│   │   ├── news/page.tsx                   # News index
│   │   ├── news/[slug]/page.tsx            # News article
│   │   └── [slug]/page.tsx                 # CMS pages (impressum, etc.)
│   ├── (payload)/admin/                    # Payload admin UI
│   │   └── [[...segments]]/page.tsx
│   ├── api/                                # API routes
│   │   ├── route.ts                        # GET /api
│   │   ├── [jurisdiction]/[year]/route.ts
│   │   ├── auto-complete/route.ts
│   │   ├── mentions/route.ts
│   │   └── [...payload]/route.ts           # Payload REST API
│   ├── stats/route.ts                      # GET /stats?q=
│   ├── pdfs/[filename]/route.ts            # PDF serving
│   ├── images/[filename]/route.ts          # Image serving
│   ├── downloads/[filename]/route.ts       # ZIP downloads
│   └── [jurisdiction]-[year].txt/route.ts  # Text export
├── collections/                            # Payload CMS definitions
│   ├── Users.ts
│   ├── NewsArticles.ts
│   ├── Pages.ts
│   └── Media.ts
├── components/                             # React components
│   ├── Navbar.tsx
│   ├── Footer.tsx
│   ├── SearchForm.tsx
│   ├── Pagination.tsx
│   ├── PageImage.tsx
│   ├── SearchHighlight.tsx
│   ├── RichText.tsx                        # Lexical rich text renderer
│   └── charts/                             # "use client" components
│       ├── TrendChart.tsx
│       ├── RegionalChart.tsx
│       ├── SearchDistributionChart.tsx
│       └── HomepageCharts.tsx
├── lib/
│   ├── db.ts                               # pg Pool for raw SQL
│   ├── queries/
│   │   ├── documents.ts
│   │   ├── search.ts
│   │   ├── stats.ts
│   │   ├── mentions.ts
│   │   └── autocomplete.ts
│   ├── report-info.ts                      # Port of report_info.py
│   ├── wordpos.ts                          # Word position loader
│   └── jurisdictions.ts
├── payload.config.ts                       # Payload configuration
├── next.config.ts
├── tailwind.config.ts
├── docker-compose.yml
├── Dockerfile
└── package.json
```

## Database Strategy

### Single PostgreSQL Instance

Both Payload CMS and the search system share one PostgreSQL database.

**Payload-managed tables** (via Drizzle ORM):
- `users`, `media`, `news_articles`, `pages` and their relation tables
- Payload handles migrations via `@payloadcms/db-postgres`

**Existing tables** (managed by Python CLI):
- `document` - report metadata
- `document_page` - page content with TSVector search index
- `token_count` - token frequencies

### Full-Text Search Access

Drizzle ORM supports TSVector via `customType`:

```typescript
import { customType, sql } from "drizzle-orm/pg-core";

const tsVector = customType<{ data: string }>({
  dataType() { return "tsvector"; },
});
```

For complex queries (ts_headline, websearch_to_tsquery, ts_rank), use Drizzle's `sql` template literals or a raw `pg` Pool connection. Both approaches work:

**Option A: Drizzle sql templates**
```typescript
const results = await db.execute(sql`
  SELECT dp.*, d.year, d.jurisdiction,
    ts_headline('pg_catalog.german', dp.content,
      websearch_to_tsquery('pg_catalog.german', ${query}),
      'MaxFragments=10, MinWords=5, MaxWords=20')
  FROM document_page dp
  JOIN document d ON dp.document_id = d.id
  WHERE dp.search_vector @@ websearch_to_tsquery('pg_catalog.german', ${query})
  ORDER BY ts_rank(dp.search_vector, websearch_to_tsquery('pg_catalog.german', ${query})) DESC
  LIMIT 20 OFFSET ${offset}
`);
```

**Option B: Raw pg Pool** (simpler, no Drizzle dependency for search)
```typescript
import { Pool } from 'pg';
const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const { rows } = await pool.query(queryText, [query, offset]);
```

Decision on which approach to use can be made during implementation. Both are safe (parameterized queries).

## Static vs Dynamic Pages

| Route | Rendering | Revalidation | Data Source |
|-------|-----------|-------------|-------------|
| `/` | Static (ISR) | 24h | DB (document counts) |
| `/berichte` | Static (ISR) | 24h | DB (document index) + report_info |
| `/[jurisdiction]/[year]` | Static (ISR) | 24h | DB (document + pages) |
| `/news` | Static (ISR) | 1h | Payload (news articles) |
| `/news/[slug]` | Static (ISR) | 1h | Payload (news article) |
| `/[slug]` (CMS pages) | Static (ISR) | 1h | Payload (pages) |
| `/suche` | SSR (`force-dynamic`) | - | DB (full-text search) |
| `/trends` | SSR (`force-dynamic`) | - | DB (token counts) |
| `/regional` | SSR (`force-dynamic`) | - | DB (mentions by jurisdiction) |

**Build-time DB access**: For `generateStaticParams`, the database must be accessible during `npm run build`. If not available (e.g., CI), use ISR with `revalidate` instead - the first request triggers generation, subsequent requests serve from cache.

## Progressive Enhancement

Core principle: **every page works without JavaScript**. JS adds interactivity.

| Feature | Without JS | With JS (enhancement) |
|---------|-----------|----------------------|
| Search | `<form method="get">` submits, server renders results | Autocomplete dropdown on input |
| Search filters | Change dropdown + click "Suchen" | `onChange` auto-submits form |
| Trends | Server-rendered data table | Chart.js interactive line chart |
| Regional | Server-rendered data table | Chart.js matrix heatmap |
| Homepage | Static stats + text content | Chart.js trend charts |
| Document viewer | `<img loading="lazy">` | Smooth scroll-to-page |
| Pagination | `<a>` links | No enhancement needed |
| Dark mode | `prefers-color-scheme` CSS | Manual toggle button |

### Search Without JS (Critical Path)

```tsx
// app/(frontend)/suche/page.tsx - Server Component
export const dynamic = 'force-dynamic';

export default async function SearchPage({ searchParams }) {
  const { q, jurisdiction, min_year, max_year, page } = await searchParams;

  // Server-side: query DB, render results
  const results = q ? await searchDocumentPages(q, { ... }) : null;

  return (
    <>
      <form action="/suche" method="get">
        <input type="text" name="q" defaultValue={q} />
        <select name="jurisdiction">...</select>
        <button type="submit">Suchen</button>
      </form>
      {results && <SearchResults results={results} />}
      {results && <Pagination current={page} total={totalPages} />}
    </>
  );
}
```

## File Serving

Route handlers serve files from `/data/` volume:

```typescript
// app/pdfs/[filename]/route.ts
export async function GET(request, { params }) {
  const { filename } = await params;
  const filePath = path.join(DATA_DIR, 'pdfs', path.basename(filename)); // path traversal prevention

  if (process.env.NODE_ENV === 'production') {
    // nginx X-Accel-Redirect (same as Flask)
    return new NextResponse(null, {
      headers: { 'X-Accel-Redirect': `/internal-pdfs/${filename}` }
    });
  }
  // Development: stream file directly
  const file = await readFile(filePath);
  return new NextResponse(file, { headers: { 'Content-Type': 'application/pdf' } });
}
```

**Do NOT use `next/image`** for document page images. They are pre-rendered at 900px in JPEG + AVIF. Use `<picture>` with native lazy loading:

```tsx
<picture>
  <source type="image/avif" srcSet={url.replace('.jpg', '.avif')} />
  <img src={url} alt={`Seite ${n}`} loading="lazy" width={900} height={1273} />
</picture>
```

## Caching Strategy

Next.js built-in caching replaces Redis entirely:

| Layer | Mechanism | Replaces |
|-------|-----------|----------|
| Static pages | ISR with `revalidate` | `@cache.cached(timeout=3600)` on page routes |
| DB queries | `unstable_cache` with tags | Redis-cached query results |
| API responses | `Cache-Control` headers | `@cache.cached(query_string=True)` |
| Search results | No cache (real-time) | Redis query_string cache |
| File responses | `Cache-Control: public, max-age=604800` | Same as current |

## Security Headers

Via `next.config.ts` `headers()` and/or `middleware.ts`:

```typescript
// next.config.ts
async headers() {
  return [{
    source: '/:path*',
    headers: [
      { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubdomains; preload' },
      { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Referrer-Policy', value: 'strict-origin' },
    ],
  }];
}
```

**CSP improvement**: Next.js supports nonce-based CSP via middleware, allowing us to remove `unsafe-inline` and `unsafe-eval` from the current CSP.

**Onion-Location**: Set via middleware to append the `.onion` equivalent URL.

## Deployment

### Docker (standalone output)

```dockerfile
FROM node:22-alpine AS base
# deps stage -> builder stage -> runner stage
# output: 'standalone' in next.config.ts
# Build requires DATABASE_URL for static generation
```

### Docker Compose (development)

```yaml
services:
  web:
    build: .
    ports: ["3000:3000"]
    volumes:
      - ./:/app
      - /app/node_modules
      - ../verfassungsschutzberichte.de/data:/data  # Share existing data
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/postgres
      DATA_DIR: /data
      PAYLOAD_SECRET: dev-secret-change-in-prod
    depends_on: [db]
  db:
    image: postgres:16-alpine
    volumes:
      - ../verfassungsschutzberichte.de/misc/dbdata:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: password
```

During development, the Next.js app shares the existing PostgreSQL data and `/data` directory from the Flask project.

### Dokku

Same deployment pattern as current:
- `dokku apps:create vsb-next`
- Link existing PostgreSQL: `dokku postgres:link vsb_db vsb-next`
- Mount data: `dokku storage:mount vsb-next /mnt/vsb:/data`
- Set env vars: `PAYLOAD_SECRET`, `DATA_DIR`
- No Redis needed (removed dependency)

### Python CLI (separate)

The Python CLI stays in the Flask project's Docker container. It runs on-demand for data ingestion (`flask update-docs`, `flask generate-images`, etc.) and writes to the shared PostgreSQL database and `/data` volume.

Long-term, the CLI could be extracted into a standalone Python package independent of Flask.
