from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_impact_service
from app.core.errors import GitOperationError, RepositoryNotFoundError
from app.schemas.impact import (
    ImpactAnalyzeRequest,
    ImpactAnalyzeResponse,
    ImpactRunResponse,
)
from app.services.impact_service import ImpactService

router = APIRouter()


@router.post("/analyze", response_model=ImpactAnalyzeResponse)
async def analyze_impact(
    body: ImpactAnalyzeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[ImpactService, Depends(get_impact_service)],
) -> ImpactAnalyzeResponse:
    try:
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
) -> ImpactRunResponse:
    try:
        return await svc.get_run(db=db, analysis_run_id=analysis_run_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
