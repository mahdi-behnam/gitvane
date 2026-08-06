from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_risk_service, get_repository_service, get_current_user
from app.db.models import User
from app.core.errors import RepositoryNotFoundError
from app.schemas.risk import RepositoryRiskResponse
from app.services.risk_service import RiskService
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.get(
    "/repositories/{repository_id}/files",
    response_model=RepositoryRiskResponse,
)
async def get_repository_risk(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[RiskService, Depends(get_risk_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    top_k: int = Query(20, ge=1, le=100),
    language: str | None = Query(None),
    include_tests: bool = Query(False),
    path_search: str | None = Query(None),
) -> RepositoryRiskResponse:
    try:
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
        return await svc.get_repository_file_risks(
            db=db,
            repository_id=repository_id,
            top_k=top_k,
            language=language,
            include_tests=include_tests,
            path_search=path_search,
        )
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
