# GitVane Frontend

GitVane frontend is a Next.js App Router application providing a modern dashboard for the
FastAPI backend.

It includes:
- **Authentication**: Email/password signup and login, GitHub & Google OAuth2, password recovery.
- **Repository Management**: Repository registration, remote branch discovery, sync & pull, and real-time SSE indexing progress.
- **Semantic Code Search**: Natural language codebase querying with match snippets and score breakdowns.
- **Change Impact Analysis**: Ripple effect prediction from Git refs, raw unified diffs, or staged files.
- **Test Recommendation**: Targeted test file identification linked to modified components.
- **Architectural Risk Ranking**: File hot spot ranking by churn, centrality, complexity, and size.
- **Interactive Graph Explorer**: File-level import and dependency graph visualization with zoom and filtering.
- **Historical Evaluation Reports**: Prediction benchmark execution, progress tracking, and Markdown report viewing.
- **Settings & API Keys**: Personal API key creation, key revocation, and MCP assistant configuration.

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

The composed frontend is served at `http://localhost:3000` (or `http://localhost` when running behind the unified Nginx application gateway). The public API URL is passed into the Next.js build through the `NEXT_PUBLIC_API_BASE_URL` build argument.

## Scripts

```bash
npm run dev                 # Start Next.js development server with hot reload
npm run lint                # Run ESLint validation
npm run format              # Check formatting with Prettier
npm run format:write        # Auto-format codebase with Prettier
npm run generate:api-types  # Generate TypeScript API types from backend OpenAPI JSON
npm run typecheck           # Validate TypeScript types
npm run test                # Run unit/component tests with Vitest
npm run test:e2e            # Run end-to-end tests with Playwright
npm run build               # Build Next.js production bundle
```

`npm run generate:api-types` requires the FastAPI backend to be running at
`http://localhost:8000`.
