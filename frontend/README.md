# Frontend (Next.js)

Next.js **App Router** application for the Litigation Prep Assistant: landing, pricing, auth entry, and dashboard flows for case input, history, and per-case results. This tree is a **scaffold**; Clerk, billing, and API integration are placeholders.

## Requirements

- Node.js **20+** (LTS recommended)
- npm (this project uses `package-lock.json`)

## Install

From this directory (`frontend/`):

```bash
npm install
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Development server with [Turbopack](https://nextjs.org/docs/app/api-reference/turbopack) (`next dev --turbopack`). |
| `npm run build` | Production build (`next build`). |
| `npm run start` | Serve the production build (`next start`). |
| `npm run lint` | ESLint via Next.js config. |

Default dev URL: `http://localhost:3000`.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Base URL of the FastAPI backend. Defaults to `http://127.0.0.1:8000` in `src/lib/api.ts` when unset. |

Create a local env file if you need overrides (for example `.env.local` — keep secrets out of git). See [Next.js Environment Variables](https://nextjs.org/docs/app/building-your-application/configuring/environment-variables).

## App Router routes (scaffold)

| Route | Purpose |
|-------|---------|
| `/` | Public landing; signed-in users are sent to `/dashboard`. |
| `/dashboard` | Authenticated home (overview + `HomeAppDetails`). |
| `/dashboard/new-scan` | New case scan with streaming `POST /api/v1/analyze`. |
| `/dashboard/scans` | Case list (`GET /api/v1/cases`). |
| `/dashboard/scans/[id]` | Case detail with agent steps. |
| `/subscriptions` | Plans / Clerk `PricingTable` + premium tools. |
| `/public/*` | Marketing-style public routes (e.g. login, pricing redirect). |

`src/proxy.ts` (Clerk middleware) controls auth at the edge; `/dashboard/*` is also gated in `dashboard/layout.tsx`.

## Components (stubs)

Under `src/components/`: domain folders for `forms`, `dashboard`, `agents`, and `ui` provide minimal placeholders for upcoming UI work.

## Deploying on Vercel

1. Import the repository in [Vercel](https://vercel.com/).
2. Set the **Root Directory** to `frontend` so installs and builds run from this folder.
3. Add `NEXT_PUBLIC_API_URL` in the project **Environment Variables** UI pointing at your deployed API (or a preview URL).

`vercel.json` in this folder sets `"framework": "nextjs"` for clarity; Vercel usually auto-detects Next.js without it.

## TypeScript and paths

`tsconfig.json` maps `@/*` to `src/*` (for example `import { apiBaseUrl } from "@/lib/api"`).
