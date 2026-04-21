# Litigation Prep Assistant

Monorepo for an AI-powered litigation preparation assistant (Kenya-focused product concept). The repository splits a **FastAPI** API and a **Next.js** (App Router) web app. See [IDEA.md](./IDEA.md) for product scope, user flows, and system design.

## Repository layout

| Directory   | Role |
|------------|------|
| `backend/` | FastAPI service: orchestration, auth validation, and API surface (scaffold). |
| `frontend/` | Next.js App Router UI: marketing, dashboard, case flows (scaffold). |

## Prerequisites

- **Backend:** Python 3.11+ and [uv](https://docs.astral.sh/uv/) (recommended), or `pip` with `backend/requirements.txt`.
- **Frontend:** Node.js 20+ (LTS recommended) and npm.

## Quick start

Run the API and the web app in two terminals.

**Terminal 1 — API**

```bash
cd backend
uv sync
uv run dev
```

The API listens on `http://127.0.0.1:8000` by default. Open `http://127.0.0.1:8000/docs` for interactive OpenAPI documentation.

**Terminal 2 — Web**

```bash
cd frontend
npm install
npm run dev
```

The app is served at `http://localhost:3000` by default.

Point the frontend at the API by setting `NEXT_PUBLIC_API_URL` in `frontend` (see [frontend/README.md](./frontend/README.md)).

## Deployment notes

- **Frontend:** Configure [Vercel](https://vercel.com/docs) with the project root set to `frontend/` (or adjust build settings accordingly). `frontend/vercel.json` declares the Next.js framework preset.
- **Backend:** Deploy to your chosen host (container, PaaS, or VM). Ensure environment variables for database, Clerk JWKS, and model providers are set when you implement those layers.

## Documentation

- [Backend README](./backend/README.md) — Python layout, dependencies, and API stubs.
- [Frontend README](./frontend/README.md) — Next.js scripts, routing, and environment variables.
