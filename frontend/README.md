# RepoLens Frontend

RepoLens frontend is a Next.js App Router application for the existing
FastAPI backend.

It includes the repository overview, repository management and indexing,
semantic search, impact analysis, test recommendation, risk ranking, dependency
graph, and evaluation report screens.

## Local Setup

```bash
npm install
npm run dev
```

The app reads the backend base URL from:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Copy `.env.example` to `.env.local` for local overrides.

When the backend runs on the host, keep the default URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Quality Checks

```bash
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

The end-to-end smoke tests use Playwright and mock the backend API from the
browser page. Install the local browser dependency once before running them:

```bash
npx playwright install chromium
```

## Docker

From the repository root:

```bash
docker compose up --build frontend
```

The composed frontend is served at `http://localhost:3000`. The public API URL
is passed into the Next.js build through the `NEXT_PUBLIC_API_BASE_URL` compose
variable, defaulting to `http://localhost:8000/api/v1` so the browser can reach
the backend through the published host port.

## Scripts

```bash
npm run dev
npm run lint
npm run format
npm run generate:api-types
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

`npm run generate:api-types` requires the FastAPI backend to be running at
`http://localhost:8000`.
