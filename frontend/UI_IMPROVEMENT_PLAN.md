# DocMind AI — Frontend UI/UX Improvement Plan

## Current architecture (unchanged)

- **Framework**: Next.js 16 (App Router) + React 19 + TypeScript (strict)
- **Styling**: Tailwind CSS v4 (`@tailwindcss/postcss`), `cva` variants, `clsx` + `tailwind-merge` via `cn()`
- **Icons**: `lucide-react`
- **State**: React Context (`lib/auth-context.tsx`) + local component state. No data-fetching library.
- **API**: single hand-rolled client `lib/api.ts` (fetch + bearer token from `localStorage`).

### Routes
| Route | Purpose |
|---|---|
| `/login`, `/register` | Auth (route group `(auth)`) |
| `/` | Dashboard: stats + recent documents |
| `/upload` | Multi-file drag & drop upload |
| `/documents` | Paginated list + filters |
| `/documents/[id]` | Detail: preview + extraction + pipeline audit |
| `/email-connections` | Roadmap/info page |
| `/notifications` | Notification center |
| `/settings` | Profile + backend health |

### Flow
`dropzone` (validate → queue) → `api.documents.upload` (FormData `files[]`, optional `document_type`) →
backend queues pipeline → documents list polls/status → `documents/[id]` polls every 2.5s while
`queued|processing` → `ExtractionView` renders `extracted_json` + `field_evidence` with per-field
confidence, inline editing (`PUT /extraction`), re-extract (`POST /reprocess`), JSON/CSV export.

### API contracts to preserve (verified against backend)
`POST /api/auth/{login,register,logout}`, `GET /api/auth/me`,
`GET /api/dashboard/stats|recent-documents`, `GET/POST/DELETE /api/documents...`,
`POST /api/documents/upload` → `{ document, message }` (returns the **primary** doc only),
`GET/PUT /api/documents/{id}/extraction`, `POST /api/documents/{id}/reprocess`,
`GET /api/documents/{id}/file?token=…`, `GET/PATCH /api/notifications…`, `GET /api/health`.

Backend limits discovered: max **10 files**/request, **50 MB**/file, extensions
`pdf, jpg, jpeg, png, webp, docx, xlsx`. Current frontend allows unlimited files and omits `webp`.

---

## Plan

### 1. Design foundation
- Semantic, theme-aware color tokens (`canvas`, `surface`, `line`, `ink`, …) + a `brand` scale,
  so light/dark are driven by tokens instead of duplicated `dark:` classes.
- Fix class-based dark mode: Tailwind v4 defaults `dark:` to `prefers-color-scheme`, but the app
  toggles `.dark` on `<html>` → add `@custom-variant dark`.
- Typography scale, tabular numerals, refined focus rings, shadows, scrollbars, `::selection`.
- A small set of keyframes; everything gated behind `prefers-reduced-motion`.

### 2. Reusable primitives (no new dependencies)
`Select`, `Alert`, `EmptyState`, `ConfidenceBar/Badge`, `Table`, `Progress`,
`Toast` provider + `ConfirmDialog` (replaces native `alert()` / `confirm()`), `PageHeader`.
Refresh `Button`, `Card`, `Badge`, `Input`, `Skeleton`, `Tabs`.

### 3. Shell
- Sidebar: cleaner nav, active indicator, mobile drawer, user footer, engine status card.
- Topbar: better search (clear button + ⌘K), theme toggle via shared context, notifications, avatar menu.
- Consistent page container/header across all dashboard routes.

### 4. Feature UX
- **Dashboard**: gradient hero, redesigned stat cards, document-type distribution, skeletons, empty state.
- **Upload**: 2-column layout, polished drag state (drag counter fixes flicker), per-file status/progress,
  success summary, validation aligned with backend limits (10 files / 50 MB / webp).
- **Documents**: filter bar, skeletons, empty/error states, pagination, responsive cards on mobile.
- **Extraction view**: confidence gauge, validation badge, sticky toolbar, field search, grouped sections,
  readable field rows (value / confidence / source evidence), containers table, dangerous-goods banner.
- **Notifications / Settings / Email connections**: restyled, consistent states.
- **Auth**: split-screen brand panel + form, inline field errors, password visibility toggle.

### 5. Verification
`npx tsc --noEmit`, `npm run lint`, `npm run build`, plus a live preview smoke test.
