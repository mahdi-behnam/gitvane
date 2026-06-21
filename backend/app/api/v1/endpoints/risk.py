from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_risk_service
from app.core.errors import RepositoryNotFoundError
from app.schemas.risk import RepositoryRiskResponse
from app.services.risk_service import RiskService

router = APIRouter()


@router.get(
    "/repositories/{repository_id}/files",
    response_model=RepositoryRiskResponse,
)
async def get_repository_risk(
    repository_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RiskService, Depends(get_risk_service)],
    top_k: int = Query(20, ge=1, le=100),
    language: str | None = Query(None),
    include_tests: bool = Query(False),
) -> RepositoryRiskResponse:
    try:
        return await svc.get_repository_file_risks(
            db=db,
            repository_id=repository_id,
            top_k=top_k,
            language=language,
            include_tests=include_tests,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
