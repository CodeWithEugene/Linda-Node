<p align="center">
  <img src="../../docs/brand/linda-node-logo-horizontal.png" alt="Linda Node" width="380" />
</p>

<h1 align="center">Linda Node web client</h1>

<p align="center">
  React 18 · TypeScript 5 · Vite 5 · Material UI v6 · TanStack Query v5 · MapLibre GL
</p>

---

## Contents

1. [Run locally](#run-locally)
2. [Screens](#screens)
3. [Source layout](#source-layout)
4. [Design system](#design-system)
5. [Brand assets and favicons](#brand-assets-and-favicons)
6. [Data fetching and state](#data-fetching-and-state)
7. [Maps](#maps)
8. [Accessibility and responsiveness](#accessibility-and-responsiveness)
9. [Bundles](#bundles)
10. [Build and test](#build-and-test)
11. [Deployment](#deployment)

---

## Run locally

```bash
cd client/frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. The Vite dev server proxies `/api`, `/cap`, and `/integration` to `http://127.0.0.1:8001`. Set `LINDA_API_ORIGIN` before starting Vite to point the proxy at a different API origin.

---

## Screens

| Route | Screen | What it does |
|---|---|---|
| `/` | **Regional Readiness** | The landing view. Ranks all 214 GHA admin-1 units by stage then exceedance probability, with stat tiles, a country rollup, a MapLibre choropleth on ICPAC vector tiles, and the grounding-evidence hashes behind the numbers. Opening a case starts from here. |
| `/signals` | **Signal Inbox** | Trigger rules, detected events, seasonal forecasts, and pipeline files with a probability meter per signal; ICPAC's own upstream action types; source health; the provenance dialog. |
| `/cases` | **Decision Cases** | Every case with its stage and state. |
| `/cases/:id` | **Case detail** | Five tabs — Evidence & trace, Actions & Readiness, Approvals, Handoffs & Exports, Audit log. |
| `/audit` | **Audit Log** | Filterable append-only hash-chained history across all cases. |
| `/library` | **Policy & Actions** | The three hazard policies with their thresholds and hashes, the action-card library, and ICPAC's indicator registry. |
| `/sources` | **Sources** | Per-adapter provenance, hashes, schema state, and refresh. |
| `/integrations` · `/developers` | **API & Partners** | Partner documentation; `/developers` is reachable without signing in. |
| `/admin` | **Admin** | Source mode, forecast issue, synthetic escalation, stop-trigger evaluation, partner keys, webhooks, demo recovery. |
| `/login` | **Sign in** | Seeded personas; the password is documented on the page. |

---

## Source layout

```
src/
├── main.tsx              React root and QueryClient
├── App.tsx               shell, routing, drawer, theme toggle, data-mode banner
├── session.tsx           session context and provider (kept separate to avoid import cycles)
├── api.ts                typed fetch client, error unwrapping, timeout, domain types
├── types.ts              response types for regional, sources, signals, verification
├── components.tsx        shared primitives — see below
├── Logo.tsx              wordmark and mark components
├── RegionalMap.tsx       MapLibre choropleth over ICPAC pg_tileserv tiles
├── AreaMap.tsx           Leaflet + OpenStreetMap per-case context map
├── mapGeometry.ts        GeoJSON centroid helper
├── theme.ts              MUI theme, light and dark
├── pages.tsx             route barrel — each feature stays its own lazy chunk
└── features/
    ├── regional.tsx      Regional Readiness
    ├── inbox.tsx         Signal Inbox and Sources
    ├── case.tsx          Decision Cases and the five case tabs
    ├── library.tsx       Policy, action cards, indicator registry
    ├── audit.tsx         Global audit log
    ├── admin.tsx         Administration
    ├── developers.tsx    Partner documentation
    └── login.tsx         Sign in
```

Shared primitives in `components.tsx`: `FreshnessBadge`, `StateChip`, `StageChip`, `HashBlock`, `CopyButton`, `ProvenanceLegend`, `SnapshotDialog`, `EmptyState`, `ErrorPanel`, plus `severityRank` / `severityColor` / `meterColor` / `relativeTime` / `money`.

---

## Design system

**Provenance colours are law**, and they mean the same thing on every screen:

| Colour | Meaning |
|---|---|
| Green | Official source — a value taken from an upstream snapshot |
| Amber | Policy assumption — a value written into the reviewed policy file |
| Blue | User entered |
| Dashed border | AI output — advisory, never authoritative |

Severity uses one scale everywhere (`severityRank`), so ICPAC's `severity_level` vocabulary and the Ready–Set–Go stages sort against each other consistently. Colour is always paired with text, never used alone.

**`StageChip` renders `null` honestly.** A case or unit that reached no stage displays *"No activation recommended"* rather than an empty slot or a defaulted stage.

**No demo chrome.** The workspace presents live data as live data. A banner appears only when something is actually wrong or unusual — a stale source, a schema failure, or an active synthetic escalation. CAP documents still carry `status=Exercise` internally, which is a standards-compliance property rather than UI framing.

---

## Brand assets and favicons

Logo masters live in [`docs/brand/`](../../docs/brand). Everything in `public/` is generated from them.

| Asset | Purpose |
|---|---|
| `favicon.ico` | Multi-resolution (16–64 px) for legacy tabs and Windows pins |
| `favicon-{16,32,48,64,96,192,256,384,512}.png` | Modern browsers, high-DPI tabs, PWA install |
| `apple-touch-icon.png` | 180 px, composited on white — iOS does not honour transparency |
| `maskable-icon-512.png` | Android adaptive icons, 20 % safe padding for the circular crop |
| `logo-horizontal.png`, `logo-horizontal-900.png` | The wordmark used in the app bar, login hero, and loader |
| `social-card.png` | 1200×630 Open Graph / Twitter preview |
| `site.webmanifest` | Name, theme colour `#E8552A`, standalone display, icon set |

`Logo.tsx` renders the wordmark. On the deep-green app bar it sits on a white plate rather than being recoloured — the artwork itself is never altered. `LogoMark` renders the umbrella alone for tight spaces.

To regenerate after a brand change, replace the masters in `docs/brand/` and re-run the Pillow script documented in the project history; sizes and padding rules are listed above.

---

## Data fetching and state

All server state goes through TanStack Query — there is no Redux and no global store. Query keys are stable and invalidated explicitly after every mutation; case detail refetches whenever a mutation returns a new `version`.

Every case mutation sends the current optimistic `version`. A stale write returns HTTP 409, which the API surfaces as a `VERSION_CONFLICT` error the UI shows with a reload prompt.

`api.ts` unwraps the `{"error": {code, message, detail}}` envelope into a plain `Error`, and aborts any request that exceeds 12 seconds so a hung upstream cannot freeze a screen.

---

## Maps

**`RegionalMap`** (MapLibre GL) draws the regional choropleth directly from ICPAC's public `pg_tileserv` admin-1 vector layer. The tiles carry `gid_1` — the same GADM identifier the statistics endpoint returns — so the join needs no intermediate geometry: a single `match` expression keyed on that property colours all 214 units. Hover shows the unit, probability, and stage; clicking opens a case. A tile failure surfaces a warning and leaves the ranking beside it untouched. The component is lazy-loaded so MapLibre stays out of the initial payload.

**`AreaMap`** (Leaflet + OpenStreetMap raster) provides per-case context from stored GeoJSON, for the cases where a single area is the subject.

---

## Accessibility and responsiveness

- Every `IconButton` carries an `aria-label`; the map container is labelled.
- Severity and freshness always pair colour with text.
- Role-gated controls are **disabled with an explanatory tooltip, never hidden**, so the permission model is visible — the API remains the enforcer.
- Every asynchronous view implements loading (skeletons shaped like the content), empty (explaining *why* it is empty), and error (with retry) states. There are no blank screens.
- The drawer collapses below `md`, grids stack, and the layout is verified at 375 px.
- Light and dark themes, with a system-default option persisted to `localStorage`.

---

## Bundles

Route-level code splitting via `React.lazy`, plus manual chunks so heavy libraries load only where used:

| Chunk | Gzipped | Loaded |
|---|---|---|
| `index` | ~45 KB | Always |
| `pages` | ~48 KB | Always |
| `maplibre` | ~217 KB | Regional map only, lazily |
| `datagrid` | ~249 KB | Screens using MUI DataGrid |
| `leaflet` | ~45 KB | Per-case map only |

Initial payload is roughly **93 KB gzipped**.

---

## Build and test

```bash
npx tsc -b --noEmit
npm test          # Vitest
npm run build
```

Tests cover the pure primitives that carry meaning across the whole UI: the severity scale, freshness labelling, `StageChip`'s null handling, `StateChip`, money and relative-time formatting, the theme in both modes, and the GeoJSON centroid helper.

---

## Deployment

On Vercel, `vercel.json` proxies `/api`, `/cap`, and `/integration` through a same-origin serverless function so the session cookie stays on the frontend origin. Set the **server-only** `LINDA_API_ORIGIN` to the public HTTPS backend origin and redeploy after changing it.

`VITE_LINDA_API_ORIGIN` remains available for deployments that deliberately call the API cross-origin. It is public build-time configuration and must never contain a secret.

Static files are served ahead of the SPA rewrite, so `/favicon.ico`, `/site.webmanifest`, and the logo assets resolve correctly.

For the container path, the production build is copied into the backend image at `/app/static` so a single container serves both the API and the web application.
