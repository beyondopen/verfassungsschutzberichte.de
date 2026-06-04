# Design System: "Aufklärung" (Editorial)

> Authoritative design reference for the Next.js migration. See `docs/prototypes/` for interactive HTML prototypes of each page.

## Direction

An editorial, content-first design inspired by The Markup and investigative journalism platforms. Trustworthy, serious, and clean. The text IS the design — generous whitespace, strong typographic hierarchy, minimal decoration.

## Prototypes

Each page has a self-contained HTML prototype in `docs/prototypes/` (Tailwind CDN, opens directly in browser):

| Page | Prototype | Route |
|------|-----------|-------|
| Homepage | `variant-b-aufklaerung.html` | `/` |
| Search | `search.html` | `/suche` |
| Reports Grid | `berichte.html` | `/berichte` |
| Document Viewer | `document.html` | `/bund/2023` |
| Trends | `trends.html` | `/trends` |
| Regional | `regional.html` | `/regional` |
| News | `blog.html` | `/news`, `/news/[slug]` |

## Color Palette

### Light Mode

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| `primary` | `#1d4ed8` | `blue-700` | Links, CTAs, active states |
| `primary-hover` | `#1e40af` | `blue-800` | Hover states |
| `bg` | `#ffffff` | `white` | Page background |
| `surface` | `#f8fafc` | `slate-50` | Alternating sections, cards |
| `text` | `#111827` | `gray-900` | Primary text |
| `text-secondary` | `#6b7280` | `gray-500` | Secondary text, captions |
| `border` | `#e5e7eb` | `gray-200` | Borders, dividers |
| `available` | `#2563eb` | `blue-600` | Report available (reports grid) |
| `missing` | `#f59e0b` | `amber-500` | Report missing (outline only, dark text) |
| `not-published` | `#d1d5db` | `gray-300` | Not published (reports grid) |
| `highlight` | `rgba(250, 204, 21, 0.35)` | — | Search term highlight on page images |
| `highlight-text` | `#fef9c3` / `bg-yellow-100` | — | `<mark>` tag for text snippets |

### Dark Mode

| Token | Hex | Tailwind | Usage |
|-------|-----|----------|-------|
| `primary` | `#3b82f6` | `blue-500` | Brighter blue on dark bg |
| `bg` | `#030712` | `gray-950` | Page background |
| `surface` | `#111827` | `gray-900` | Cards, sections |
| `text` | `#f3f4f6` | `gray-100` | Primary text |
| `text-secondary` | `#9ca3af` | `gray-400` | Secondary text |
| `border` | `#1f2937` | `gray-800` | Borders |
| `highlight-text` | `rgba(113, 63, 18, 0.5)` | `yellow-900/50` | `<mark>` in dark mode |

### Contrast Ratios (WCAG AA verified)

- `text` on `bg`: #111827 on #ffffff = 16.8:1 (AAA)
- `primary` on `bg`: #1d4ed8 on #ffffff = 5.1:1 (AA)
- `text-secondary` on `bg`: #6b7280 on #ffffff = 5.4:1 (AA)
- `missing` (#f59e0b) on white: 2.7:1 — **only as background fill with dark text, never as standalone text**

## Typography

### Font Stacks

```css
/* Headings: editorial serif */
--font-serif: "Source Serif 4", Georgia, serif;

/* Body: system sans-serif (zero load time) */
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;

/* Data / labels */
--font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
```

Source Serif 4 is loaded from Google Fonts (400, 600, 700 weights). All other fonts are system fonts.

### Scale

| Token | Size | Usage |
|-------|------|-------|
| `text-xs` | 0.75rem | Badges, labels |
| `text-sm` | 0.875rem | Captions, metadata, nav links |
| `text-base` | 1rem | Body text |
| `text-lg` | 1.125rem | News article body, lead text |
| `text-xl` | 1.25rem | Subheadings |
| `text-2xl` | 1.5rem | Card titles, testimonial names |
| `text-3xl` | 1.875rem | Section headers (h2) |
| `text-4xl` | 2.25rem | Page titles (h1) |
| `text-5xl` | 3rem | Homepage hero heading |
| `text-6xl` | 3.75rem | Hero heading on large screens |

### Properties

- **Headings**: Source Serif 4, font-bold (700), tracking-tight, leading-tight (1.2)
- **Body**: System sans-serif, font-normal (400), leading-relaxed (1.625)
- **Hyphenation**: `hyphens: auto` on body (essential for German)
- **News articles**: text-lg, leading-relaxed, max-w-3xl for optimal line length (~65 chars)

## Page Layouts

### Homepage (see `variant-b-aufklaerung.html`)

- **Hero**: Two-column (3+2 on lg). Left: large serif heading "Über was informiert der Verfassungsschutz?", subtitle, CTA buttons. Right: stats card (487 Berichte, 17 Behörden, seit 1950) + Bundesland table.
- **Search band**: Full-width blue-700 bg, centered search form, example query links.
- **Features**: 3-column grid (Suche, Trends, Regional) with icons and arrow links.
- **Charts**: 2-column placeholder cards on gray-50 bg.
- **Testimonials**: 4 full quotes with blue left border, serif italic text.
- **Offene Daten**: 3-column card grid (PDFs, Texte, API).
- **Partner:innen**: Grid of partner names.
- **Kontakt**: Email, PGP, social links.
- **FAQ**: `<details>`/`<summary>` collapsible sections.
- **Newsletter**: Centered card with email input.
- **Footer**: 4-column dark layout.

### Search (see `search.html`)

- **Form**: Large input + jurisdiction/year dropdowns + submit. Real `<form method="get">`.
- **Results**: Count + page info header. Cards with page thumbnail (w-40 h-56) on left with yellow highlight boxes, snippets with `<mark>` on right. Badge for jurisdiction+year.
- **Pagination**: `<a>` links, Previous/1/2/3.../18/Next.
- **Chart placeholder**: Small year distribution bar below results header.

### Reports Grid (see `berichte.html`)

- **Legend**: Blue/amber/gray color key at top.
- **Grid**: One section per jurisdiction (Bund first, then alphabetical). Flex-wrap of small colored year cells. Available = blue `<a>` tags, missing = amber outline `<span>`, not published = gray `<span>`.
- **Offene Daten**: Download links at bottom.

### Document Viewer (see `document.html`)

- **Header**: Back link, jurisdiction badge, serif title, metadata row (pages, words).
- **Actions**: PDF download (primary), Text/JSON (outline).
- **Legal note**: Amber warning box about VS not being neutral.
- **Pages**: Vertically stacked A4 aspect-ratio image placeholders with page numbers. `loading="lazy"`.
- **Related**: Year pills linking to other reports from same jurisdiction.

### Trends (see `trends.html`)

- **Form**: Term input + "Hinzufügen" button. Active terms as blue pill tags with × remove buttons (each in own `<form>` for no-JS). Suggestions row.
- **Chart**: Large card with SVG mockup line chart (two polylines). Placeholder for Chart.js.
- **Export**: JPG, CSV, Link buttons.
- **Data table**: `<details>` collapsible table (no-JS fallback).
- **Methodology**: Small text note.

### Regional (see `regional.html`)

- **Form**: Term input pre-filled.
- **Heatmap**: Full HTML table (17 jurisdictions × 10 years). Cells color-coded in 5-tier blue gradient. Sticky first column. Horizontal scroll on mobile.
- **Legend**: Color scale explanation.
- **Export**: CSV, Link buttons.

### News (see `blog.html`, renamed from Blog)

- **Index** (`/news`): Date (font-mono) + serif title (link) + excerpt + tags. Posts separated by dividers.
- **Article** (`/news/[slug]`): Back link, date, large serif h1, tags. Body at text-lg, max-w-3xl, leading-relaxed. Serif h2 subheadings, blue-border blockquotes, styled lists.

## Component Inventory

| Component | Type | Used On | Key Details |
|-----------|------|---------|-------------|
| `Navbar` | Server | All | Sticky, serif logo, nav links, dark mode toggle, mobile hamburger |
| `Footer` | Server | All | 4-column dark layout, social links, copyright |
| `DarkModeToggle` | Client | Navbar | Moon/sun icon, localStorage + prefers-color-scheme |
| `SearchForm` | Server | Homepage, /suche | `<form method="get">`, dropdowns, works without JS |
| `SearchResultCard` | Server | /suche | Thumbnail + highlight boxes + snippets + badge |
| `SearchHighlight` | Server | /suche | Absolutely positioned yellow divs over thumbnail |
| `Pagination` | Server | /suche | `<a>` links, disabled prev/next states |
| `PageImage` | Server | /[j]/[y], /suche | `<picture>` AVIF+JPEG, loading="lazy" |
| `ReportGrid` | Server | /berichte | Flex-wrap year cells, color-coded |
| `StatCard` | Server | Homepage | Stats (487, 17, 1950) + Bundesland table |
| `RichText` | Server | /news, CMS pages | Renders Payload Lexical content |
| `HomepageCharts` | Client | Homepage | Chart.js v4 line charts |
| `TrendChart` | Client | /trends | Multi-term line chart, export |
| `RegionalHeatmap` | Client | /regional | Chart.js matrix OR HTML table |
| `SearchDistChart` | Client | /suche | Year distribution mini-chart |
| `NewsletterForm` | Server | Footer | Email input, Listmonk POST |
| `FAQSection` | Server | Homepage | `<details>`/`<summary>`, no JS needed |
| `TermPills` | Server | /trends | Removable term tags in `<form>` wrappers |

## Accessibility (WCAG AA)

### Fixes from Current Site
- Remove `user-scalable=0` from viewport meta
- Add skip-to-content link: "Zum Inhalt springen"
- Fix heading hierarchy: h1 → h2 → h3 (no skipping)
- Proper form labels (no generic IDs)
- Descriptive image alt text: "Seite 156 des Verfassungsschutzberichts 2023 Bund"

### New Requirements
- All text/background combinations meet 4.5:1 contrast
- Visible focus indicators on all interactive elements
- All interactive elements keyboard-accessible
- Proper ARIA landmarks: `<nav>`, `<main>`, `<footer>`
- Disabled states use `<button disabled>` or `<span>`, not fake disabled links

## Dark Mode

- Tailwind `class` strategy (manual toggle + `prefers-color-scheme` fallback)
- `<html class="dark">` toggled via button, persisted to `localStorage`
- Without JS: `prefers-color-scheme` media query applies automatically
- Toggle button: moon icon (light mode), sun icon (dark mode)
- Chart.js colors swap via CSS custom properties

## Responsive Breakpoints

Tailwind defaults: `sm` (640px), `md` (768px), `lg` (1024px), `xl` (1280px)

| Element | Mobile | Desktop |
|---------|--------|---------|
| Navbar | Hamburger menu | Inline links |
| Hero | Stacked (heading, then stats card) | Side-by-side 3+2 grid |
| Search results | Thumbnail above snippets | Thumbnail left, snippets right |
| Reports grid | Wraps naturally | Dense rows |
| Regional heatmap | Horizontal scroll, sticky first col | Full table visible |
| News article | Full-width, text-base | max-w-3xl centered, text-lg |

## Chart.js v4

- Register components explicitly (tree-shaking)
- Dark mode: swap colors via CSS custom properties
- **No-JS fallback**:
  - Homepage: stats visible, charts hidden
  - Trends: `<details>` data table with year/term columns
  - Regional: full HTML heatmap table (works without JS by default)
  - Search: year distribution hidden, results fully functional
