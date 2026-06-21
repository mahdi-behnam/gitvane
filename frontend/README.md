# RepoLens Frontend

RepoLens frontend is a Next.js App Router application for the existing
FastAPI backend.

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

## Scripts

```bash
npm run dev
npm run lint
npm run format
npm run generate:api-types
npm run typecheck
npm run build
```

`npm run generate:api-types` requires the FastAPI backend to be running at
`http://localhost:8000`.
