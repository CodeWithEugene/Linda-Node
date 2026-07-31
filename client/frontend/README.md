# Linda Protocol web client

The web client is a React 18, TypeScript, Vite, and Material UI single-page application for the Linda Protocol exercise workflow.

## Run locally

```bash
cd client/frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development server proxies `/api`, `/cap`, and `/integration` to `http://127.0.0.1:8001` by default. Set `LINDA_API_ORIGIN` before starting Vite to point the development proxy at another API origin.

For a Vercel deployment, `vercel.json` proxies `/api`, `/cap`, and `/integration` through a same-origin serverless proxy. Set the server-only `LINDA_API_ORIGIN` environment variable in the Vercel project to the public HTTPS backend origin. This keeps the cookie session on the frontend origin. `VITE_LINDA_API_ORIGIN` remains available for deployments that deliberately call the API directly; it is public build-time configuration and must never contain a secret.

## Screens

- **Signal Inbox**: inspects live, cached, stale, or replayed signals and creates source-backed cases.
- **Decision Cases**: presents evidence, deterministic policy gates, action cards, readiness tasks, approval signatures, exports, and per-case audit history.
- **Sources**: shows snapshot provenance, freshness, hashes, schema state, and refresh controls.
- **Audit Log**: lists the append-only hash-chained event history.
- **Policy & Actions**: renders the read-only, hash-pinned YAML policy and action-card library.
- **Admin**: restores demo data and manages integration keys and webhook subscriptions.

The client uses TanStack Query for server state. Role-gated controls remain visible but disabled, while the API remains the enforcement layer.

## Build and test

```bash
npm run build
npm test -- --passWithNoTests
```

The production build is copied into the backend Docker image so one container can serve the API and web application.
