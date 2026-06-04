# Payload CMS Integration

## Overview

Payload CMS v3 runs embedded inside the Next.js 16 application (same process, same server). It provides:
- Admin UI at `/admin` for content management
- PostgreSQL storage via `@payloadcms/db-postgres` (Drizzle ORM)
- Authentication with role-based access control
- Rich text editing via Lexical
- Media/file upload management
- REST and GraphQL APIs (auto-generated)

## Configuration

```typescript
// payload.config.ts
import { buildConfig } from 'payload'
import { postgresAdapter } from '@payloadcms/db-postgres'
import { lexicalEditor } from '@payloadcms/richtext-lexical'

export default buildConfig({
  secret: process.env.PAYLOAD_SECRET,
  db: postgresAdapter({
    pool: { connectionString: process.env.DATABASE_URL },
    push: false,          // Don't auto-push, use migrations
    migrationDir: './migrations',
  }),
  editor: lexicalEditor({}),
  collections: [Users, NewsArticles, Pages, Media],
  admin: {
    user: 'users',        // Which collection handles auth
  },
})
```

## Collections

### Users

Handles authentication and role-based access.

```typescript
// collections/Users.ts
export const Users: CollectionConfig = {
  slug: 'users',
  auth: true,
  admin: {
    useAsTitle: 'name',
  },
  fields: [
    { name: 'name', type: 'text', required: true },
    {
      name: 'roles',
      type: 'select',
      hasMany: true,
      options: ['admin', 'editor', 'contributor'],
      defaultValue: ['contributor'],
      required: true,
      saveToJWT: true,  // Available in JWT without DB lookup
      access: {
        update: ({ req: { user } }) => user?.roles?.includes('admin'),
      },
    },
  ],
}
```

**Roles**:
| Role | Can Do |
|------|--------|
| `admin` | Full access: manage users, publish everything, change settings |
| `editor` | Create and publish news articles, edit pages, upload media |
| `contributor` | Create draft news articles (must be approved by editor/admin to publish) |

### NewsArticles

Rich text news articles with Lexical editor.

```typescript
// collections/NewsArticles.ts
export const NewsArticles: CollectionConfig = {
  slug: 'news-articles',
  admin: {
    useAsTitle: 'title',
    defaultColumns: ['title', 'publishedDate', 'status'],
  },
  versions: { drafts: true },  // Enable draft/publish workflow
  fields: [
    { name: 'title', type: 'text', required: true },
    { name: 'slug', type: 'text', required: true, unique: true },
    {
      name: 'publishedDate',
      type: 'date',
      required: true,
      admin: { date: { pickerAppearance: 'dayOnly' } },
    },
    {
      name: 'content',
      type: 'richText',  // Lexical editor
      required: true,
    },
    {
      name: 'tags',
      type: 'array',
      fields: [{ name: 'tag', type: 'text' }],
    },
    {
      name: 'featuredImage',
      type: 'upload',
      relationTo: 'media',
    },
  ],
  access: {
    read: () => true,  // Public
    create: ({ req: { user } }) =>
      user?.roles?.some(r => ['admin', 'editor', 'contributor'].includes(r)),
    update: ({ req: { user } }) =>
      user?.roles?.some(r => ['admin', 'editor'].includes(r)),
    delete: ({ req: { user } }) =>
      user?.roles?.includes('admin'),
  },
}
```

### Pages

CMS-managed static pages (Impressum, About, etc.).

```typescript
// collections/Pages.ts
export const Pages: CollectionConfig = {
  slug: 'pages',
  admin: {
    useAsTitle: 'title',
  },
  fields: [
    { name: 'title', type: 'text', required: true },
    { name: 'slug', type: 'text', required: true, unique: true },
    { name: 'content', type: 'richText', required: true },
  ],
  access: {
    read: () => true,
    create: ({ req: { user } }) =>
      user?.roles?.some(r => ['admin', 'editor'].includes(r)),
    update: ({ req: { user } }) =>
      user?.roles?.some(r => ['admin', 'editor'].includes(r)),
    delete: ({ req: { user } }) =>
      user?.roles?.includes('admin'),
  },
}
```

### Media

Image and file uploads for news articles and pages.

```typescript
// collections/Media.ts
export const Media: CollectionConfig = {
  slug: 'media',
  upload: {
    staticDir: 'media',
    imageSizes: [
      { name: 'thumbnail', width: 400, height: 300, position: 'centre' },
      { name: 'card', width: 768, height: undefined, position: 'centre' },
    ],
    mimeTypes: ['image/*'],
  },
  fields: [
    { name: 'alt', type: 'text', required: true },
  ],
  access: {
    read: () => true,
    create: ({ req: { user } }) =>
      user?.roles?.some(r => ['admin', 'editor', 'contributor'].includes(r)),
  },
}
```

## Coexistence with Search Tables

Payload manages its own tables via Drizzle (users, news_articles, pages, media, and their relations). The existing search tables (document, document_page, token_count) are **not** Payload collections - they live in the same PostgreSQL database but are managed independently.

```
PostgreSQL Database
├── Payload tables (Drizzle managed)
│   ├── users
│   ├── news_articles
│   ├── pages
│   ├── media
│   └── ... (relation tables, versions, etc.)
│
└── Search tables (Python CLI managed)
    ├── document
    ├── document_page (with TSVector index)
    └── token_count
```

**No conflicts**: Payload only touches tables it creates. The search tables were created by SQLAlchemy and are written to by the Python CLI. The Next.js app reads them via raw SQL or a separate `pg` Pool.

**Migrations**: Payload uses its own migration system (`payload migrate`). The search tables don't need Payload migrations - they're stable and only change if we restructure the document schema (which would require coordinating with the Python CLI).

## Content Migration

### Existing News Articles (4 total)

Current markdown files in `src/news/posts/`:
1. `2019-11-02-launch.md` - Site launch announcement
2. `2020-01-03-36c3.md` - 36C3 conference post
3. `2020-05-04-urteil-im-anhang.md` - Court ruling analysis
4. `2021-06-21-neue-berichte-neues-feature.md` - New reports and features

**Migration options**:
1. **Manual**: Create each post in Payload admin UI, copy-paste content. Quick for 4 posts.
2. **Seed script**: Write a `payload.seed.ts` that reads the markdown files, converts to Lexical JSON, and creates Payload documents programmatically.
3. **Markdown field**: Use a Payload markdown field instead of rich text for backward compatibility. Simpler but loses Lexical's editing benefits.

**Recommendation**: Manual for 4 posts. Write new content in Lexical going forward.

### Impressum Page

Currently a Jinja2 template (`src/templates/impressum.html`). Create as a Payload Page with slug `impressum`. Content is static legal text that editors can update via the admin UI.

## Rendering CMS Content

### News Articles

```tsx
// app/(frontend)/news/[slug]/page.tsx
import { getPayload } from 'payload'
import config from '@payload-config'
import { RichText } from '@/components/RichText'

export default async function NewsArticle({ params }) {
  const { slug } = await params
  const payload = await getPayload({ config })

  const { docs } = await payload.find({
    collection: 'news-articles',
    where: { slug: { equals: slug } },
    limit: 1,
  })

  if (!docs.length) notFound()
  const post = docs[0]

  return (
    <article>
      <h1>{post.title}</h1>
      <time>{post.publishedDate}</time>
      <RichText content={post.content} />
    </article>
  )
}
```

### CMS Pages

```tsx
// app/(frontend)/[slug]/page.tsx
// Catches /impressum, /about, etc. from Payload Pages collection
export default async function CMSPage({ params }) {
  const { slug } = await params
  const payload = await getPayload({ config })
  const { docs } = await payload.find({
    collection: 'pages',
    where: { slug: { equals: slug } },
  })
  if (!docs.length) notFound()
  return <RichText content={docs[0].content} />
}
```

### RichText Component

Payload provides `@payloadcms/richtext-lexical/react` for rendering Lexical content as React components. This handles headings, paragraphs, lists, links, images, code blocks, etc.

## Admin UI

Payload's admin UI is served at `/admin` via the `(payload)` route group. It includes:
- Dashboard with collection overview
- News article editor with Lexical rich text
- Page editor
- Media library (upload, browse, delete)
- User management (create, assign roles)
- Version history for news articles (drafts)

The admin UI is React-based and requires JavaScript. It is not part of the public-facing site and does not need to work without JS.

## Future: Document Metadata in Payload

Currently, document metadata (title, jurisdiction, year) lives in the `document` table managed by the Python CLI. A future enhancement could:

1. Create a Payload `Documents` collection for metadata
2. Have the Python CLI write to Payload's API instead of directly to SQL
3. Enable editors to add annotations, corrections, or additional metadata via the admin UI
4. Support new document types beyond Verfassungsschutzberichte

This is out of scope for the initial migration but the architecture supports it.
