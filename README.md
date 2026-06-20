# RepoLens

RepoLens is an AI-assisted software engineering system that analyzes Git repositories, builds dependency graphs, mines commit histories, computes semantic embeddings, and predicts change impact risk and test recommendations.

This is a serious portfolio/research project backend, prioritizing deterministic evidence and structured logic over black-box LLM predictions.

## Core Features
1. **Repository Ingestion & Git Mining**: Clones and inspects repositories, tracking history and file changes.
2. **Language-Aware Parsing**: Best-effort AST analysis for Python and Tree-sitter for JS/TS to extract classes, functions, and imports.
3. **Dependency Graph Builder**: Constructs in-memory and database-backed representation of file and symbol dependencies.
4. **Hybrid Impact Prediction Engine**: Ranks files potentially impacted by a code change using a weighted formula of dependency relationships, semantic similarity, and commit co-changes.
5. **Historical Evaluation Harness**: Validates predictive accuracy on past commits using information retrieval metrics (Precision@K, Recall@K, MAP, NDCG, MRR).
6. **LLM Explanation Layer**: Leverages NVIDIA NIM to generate human-readable summaries of deterministic impact evidence.

## Technology Stack
- **Backend Core**: Python 3.11+ / FastAPI / Pydantic v2
- **Database**: PostgreSQL with `pgvector` / SQLAlchemy 2.0 Async / Alembic
- **Task Queue**: Redis / RQ (or Celery)
- **Code Analysis**: GitPython, Python AST, Tree-sitter, NetworkX
- **Machine Learning**: Sentence-Transformers (`jinaai/jina-embeddings-v2-base-code`)
- **LLM/Embeddings API**: NVIDIA NIM API

## Getting Started

### Local Development Setup

1. **Clone and navigate to the project directory**:
   ```bash
   cd repolens
   ```

2. **Prepare Environment**:
   Copy `.env.example` to `.env` and fill in necessary fields:
   ```bash
   cp .env.example .env
   ```

3. **Install dependencies inside the virtual environment**:
   Make sure you activate the virtual environment at `venv/`:
   ```powershell
   .\venv\Scripts\activate
   ```
   Then install the requirements:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

## Documentation
Additional documentation can be found in the `docs/` folder:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Deep dive into architecture and data flow.
- [docs/EVALUATION.md](docs/EVALUATION.md) - Historical commit evaluation details.
- [docs/API.md](docs/API.md) - API endpoints description and curl examples.
- [docs/RESUME_BULLETS.md](docs/RESUME_BULLETS.md) - Professional experience framing.
