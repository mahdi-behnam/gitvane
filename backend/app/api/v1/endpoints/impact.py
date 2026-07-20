from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_impact_service, get_repository_service, get_current_user
from app.db.models import User, AnalysisRun
from app.core.errors import GitOperationError, RepositoryNotFoundError
from app.schemas.impact import (
    ImpactAnalyzeRequest,
    ImpactAnalyzeResponse,
    ImpactRunResponse,
)
from app.services.impact_service import ImpactService
from app.services.repository_service import RepositoryService

router = APIRouter()


@router.post("/analyze", response_model=ImpactAnalyzeResponse)
async def analyze_impact(
    body: ImpactAnalyzeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[ImpactService, Depends(get_impact_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ImpactAnalyzeResponse:
    try:
        await repo_svc.get_repository_or_raise(db=db, repository_id=body.repository_id, owner_id=current_user.id)
        return await svc.analyze(db=db, request=body)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (GitOperationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/runs/{analysis_run_id}", response_model=ImpactRunResponse)
async def get_impact_run(
    analysis_run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[ImpactService, Depends(get_impact_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ImpactRunResponse:
    try:
        stmt = select(AnalysisRun.repository_id).where(AnalysisRun.id == analysis_run_id)
        result = await db.execute(stmt)
        repository_id = result.scalar_one_or_none()
        if repository_id is None:
            raise RepositoryNotFoundError(f"Analysis run with id={analysis_run_id} does not exist")
        
        await repo_svc.get_repository_or_raise(db=db, repository_id=repository_id, owner_id=current_user.id)
        return await svc.get_run(db=db, analysis_run_id=analysis_run_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
