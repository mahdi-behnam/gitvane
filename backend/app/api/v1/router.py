from fastapi import APIRouter

from app.api.v1.endpoints import (
    evaluation,
    graph,
    health,
    impact,
    indexing,
    repositories,
    risk,
    search,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(
    repositories.router, prefix="/repositories", tags=["repositories"]
)
api_router.include_router(
    indexing.router, prefix="/repositories", tags=["indexing"]
)  # prefix is nested under repositories
api_router.include_router(impact.router, prefix="/impact", tags=["impact"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
