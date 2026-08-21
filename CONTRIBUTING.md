# Contributing to GitVane

Thank you for your interest in contributing to **GitVane**!

GitVane is an AI-assisted software engineering platform that analyzes Git repositories to predict the ripple effects of code changes, recommend targeted tests, score architectural risks, and integrate with AI coding agents via the Model Context Protocol (MCP).

This document outlines the guidelines and workflow for contributing to GitVane. Following these practices helps keep the codebase robust, maintainable, and aligned with core architectural principles.

---

## Table of Contents

- [Core Principles & Architectural Invariants](#core-principles--architectural-invariants)
- [Code of Conduct & Licensing](#code-of-conduct--licensing)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
- [Development Setup Options](#development-setup-options)
  - [Option 1: Full Docker Compose (Containerized)](#option-1-full-docker-compose-containerized)
  - [Option 2: Hybrid Local Development (Recommended for Fast Iteration)](#option-2-hybrid-local-development-recommended-for-fast-iteration)
- [Backend Development (Python / FastAPI / Celery)](#backend-development-python--fastapi--celery)
  - [Setup with `uv`](#setup-with-uv)
  - [Database Migrations (Alembic)](#database-migrations-alembic)
  - [Running Backend Services](#running-backend-services)
  - [Linting, Formatting & Tests](#linting-formatting--tests)
- [Frontend Development (Next.js / TypeScript)](#frontend-development-nextjs--typescript)
  - [Setup with `npm`](#setup-with-npm)
  - [Syncing API Types](#syncing-api-types)
  - [Linting, Formatting & Typechecking](#linting-formatting--typechecking)
  - [Testing (Vitest & Playwright)](#testing-vitest--playwright)
- [MCP Server Development (`gitvane-mcp`)](#mcp-server-development-gitvane-mcp)
- [Contributing Workflow & Pull Requests](#contributing-workflow--pull-requests)
  - [Branch Naming](#branch-naming)
  - [Commit Message Conventions (50/72 Rule)](#commit-message-conventions-the-5072-rule)
  - [Pull Request Checklist](#pull-request-checklist)

---

## Core Principles & Architectural Invariants

Before writing code, please keep these fundamental design decisions in mind:

1. **Deterministic-First Foundation**:
   - GitVane's prediction scores and blast radius calculations are grounded in **deterministic software engineering evidence**: language-aware AST parsing, static dependency graphs, historical commit co-change mining, pgvector similarity, and structural risk metrics.
   - LLMs are strictly used to **summarize and explain already-computed evidence**. Never rely on LLM hallucinations to invent dependencies or score file impacts.
2. **Transactional Outbox & Asynchronous Processing**:
   - Long-running tasks (repository cloning, AST parsing, embedding generation, evaluation benchmarks) must never block synchronous HTTP requests.
   - Mutation endpoints create immutable generation state and write to the transactional outbox in the same database transaction. The outbox dispatcher and Celery workers handle execution asynchronously.
3. **Immutability & Safety**:
   - Prefer pure functions and immutable data structures where practical.
   - Always validate user inputs at system boundaries using Pydantic models (backend) and Zod schemas (frontend).
4. **Zero Hardcoded Secrets**:
   - Never commit API keys, personal access tokens, or credentials. Use environment variables and `.env` files.

---

## Code of Conduct & Licensing

- **Respectful Collaboration**: We strive to provide a welcoming, collaborative, and harassment-free environment for everyone.
- **License**: GitVane is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE). By contributing to this repository, you agree that your contributions will be licensed under the same terms.

---

## Getting Started

### Prerequisites

- **Git** 2.40+
- **Docker** and **Docker Compose** v2+
- **Python** 3.11, 3.12, or 3.13 (Managed via [`uv`](https://docs.astral.sh/uv/))
- **Node.js** 20+ (LTS) & **npm** 10+

### Environment Configuration

Copy the example environment configuration to `.env` in the repository root:

```bash
cp .env.example .env
```

Review `.env` and configure your environment:
- **`EMBEDDING_PROVIDER`**: Default is `local` (uses `sentence-transformers/all-MiniLM-L6-v2` locally). Set to `nim` if using NVIDIA NIM.
- **`NVIDIA_API_KEY`**: Optional, required only when `EMBEDDING_PROVIDER=nim` or LLM explanations are enabled via NVIDIA NIM.
- **`SECRET_KEY`**: Provide a secure random secret key for session signing and authentication.

---

## Development Setup Options

### Option 1: Full Docker Compose (Containerized)

To spin up the entire GitVane stack (PostgreSQL + pgvector, Redis, RabbitMQ, Celery workers, Outbox Dispatcher, Reconciler, FastAPI backend, Next.js frontend, and Nginx gateway):

```bash
# Build and start all services
docker compose up --build

# Or run in detached mode
docker compose up -d --build
```

- **Frontend Application Gateway**: `http://localhost` (or `http://localhost:3000`)
- **Backend REST API & Swagger Docs**: `http://localhost:8000/docs`
- **PostgreSQL / pgvector**: `localhost:5432`

To stop services:
```bash
docker compose down
```

---

### Option 2: Hybrid Local Development (Recommended for Fast Iteration)

For day-to-day coding, running background infrastructure in Docker while running the FastAPI backend and Next.js frontend directly on your host provides instant hot-reloading and simpler debugging.

#### Step 1: Start Infrastructure in Docker

Start only the database, cache, and message broker:

```bash
docker compose up -d db redis rabbitmq
```

#### Step 2: Run Backend & Workers on Host

See [Backend Development](#backend-development-python--fastapi--celery) below.

#### Step 3: Run Frontend on Host

See [Frontend Development](#frontend-development-nextjs--typescript) below.

---

## Backend Development (Python / FastAPI / Celery)

The backend is located in [`backend/`](backend/) and managed with `uv`.

### Setup with `uv`

```bash
cd backend
uv sync --all-extras
```

### Database Migrations (Alembic)

Whenever database models are modified in `app/models/`:

```bash
cd backend

# Create a new migration revision
uv run alembic revision --autogenerate -m "describe your migration"

# Apply pending migrations
uv run alembic upgrade head
```

### Running Backend Services

In separate terminals:

1. **FastAPI Web Server**:
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
   ```

2. **Celery Task Worker**:
   ```bash
   cd backend
   uv run celery -A app.core.celery_app worker -Q indexing_cpu,workflow_control,evaluation_cpu --loglevel=info -P solo
   ```

3. **Outbox Dispatcher**:
   ```bash
   cd backend
   uv run python -m app.cli.dispatcher
   ```

4. **Outbox Reconciler**:
   ```bash
   cd backend
   uv run python -m app.cli.reconciler
   ```

### Linting, Formatting & Tests

We use `ruff` for linting and code formatting, and `pytest` for testing:

```bash
cd backend

# Check linting rules
uv run ruff check app tests

# Auto-format code
uv run ruff format app tests

# Run test suite
uv run pytest -v

# Run tests with coverage report
uv run pytest --cov=app tests/
```

---

## Frontend Development (Next.js / TypeScript)

The frontend is located in [`frontend/`](frontend/) and built with Next.js App Router, Tailwind CSS, Radix UI, Lucide icons, and XYFlow.

### Setup with `npm`

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### Syncing API Types

When backend REST schemas change, regenerate the TypeScript API contracts from the running FastAPI OpenAPI schema:

```bash
# Ensure backend is running at http://localhost:8000
cd frontend
npm run generate:api-types
```

### Linting, Formatting & Typechecking

```bash
cd frontend

# Lint check with ESLint
npm run lint

# Check formatting with Prettier
npm run format

# Auto-format with Prettier
npm run format:write

# TypeScript type validation
npm run typecheck
```

### Testing (Vitest & Playwright)

```bash
cd frontend

# Run unit & component tests
npm run test

# Run Playwright end-to-end tests (requires Playwright browser)
npx playwright install chromium # First time only
npm run test:e2e
```

---

## MCP Server Development (`gitvane-mcp`)

The Model Context Protocol server is located in [`mcp/`](mcp/) and allows AI assistants to query GitVane intelligence.

### Local Installation for Development

```bash
cd mcp
pip install -e .
```

### Running MCP Locally

```bash
gitvane-mcp --server-url http://localhost:8000 --api-key <your-api-key>
```

When modifying MCP tool definitions (`gitvane_analyze_impact`, `gitvane_recommend_tests`, `gitvane_get_file_risk`), verify backward compatibility and update [`mcp/README.md`](mcp/README.md) accordingly.

---

## Contributing Workflow & Pull Requests

### Branch Naming

Use descriptive branch names with appropriate prefixes:

- `feat/add-rust-parser`
- `fix/outbox-event-deadlock`
- `docs/update-api-reference`
- `refactor/extract-graph-builder`
- `test/add-impact-eval-tests`

### Commit Message Conventions (The 50/72 Rule)

We follow the classic **50/72 Git Commit Formatting Standard** (often referred to as the **50/72 Rule** or *Tim Pope's Git Style*):

#### 1. The 50/72 Formatting Rule

1. **Subject Line (Title)**:
   - Keep the subject line to **50 characters or less**.
   - Capitalize the first letter.
   - Do **not** end the subject line with a period.
   - Use the **imperative mood** (e.g., `Add feature X`, `Fix bug Y`, `Refactor module Z`). A good rule of thumb is that it should complete the sentence: *"If applied, this commit will..."*.
2. **Separation**:
   - Always leave exactly **one blank line** between the subject line and the body.
3. **Body (Description)**:
   - Wrap lines in the body at **72 characters or less**.
   - Explain the **what** and **why** of the change, not the *how* (the diff already shows the *how*).

#### 2. When to Include a Body Description

- **No description needed**: If the change is small, self-contained, and fully described by the 50-character title (e.g., `Fix spelling mistake in README`).
- **Description required**: If the change is complex, has architectural implications, introduces new behavior, fixes a subtle bug, or requires explaining design rationale.

#### Examples

**Simple Change (Title Only):**
```
Fix spelling mistake in README
```

**Complex Change (Title and Wrapped Description):**
```
Refactor database connection pool

Separate connection lifecycle management from the query runner to
prevent connection leaks under high concurrent load.

Also increase default pool size to 20 to support the upcoming
analytics dashboard features.
```

### Pull Request Checklist

Before submitting a pull request, please ensure:

- [ ] Code follows project formatting standards (`uv run ruff format` and `npm run format:write`).
- [ ] All linters pass without errors or warnings (`uv run ruff check` and `npm run lint`).
- [ ] TypeScript compiles cleanly without errors (`npm run typecheck`).
- [ ] All unit and integration tests pass (`uv run pytest` and `npm run test`).
- [ ] New features or bug fixes include corresponding unit or integration tests (aiming for 80%+ test coverage).
- [ ] Database schema changes include a generated and tested Alembic migration script.
- [ ] Frontend API types are updated if backend endpoint schemas changed (`npm run generate:api-types`).
- [ ] Documentation (`README.md`, `docs/`, or docstrings) has been updated for public-facing changes.
- [ ] No hardcoded secrets, credentials, or local environment paths are committed.

Thank you for helping make GitVane better!
