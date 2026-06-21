from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_evaluation_service
from app.core.errors import RepositoryNotFoundError
from app.schemas.evaluation import (
    EvaluationReportResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationStatusResponse,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    body: EvaluationRunRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationRunResponse:
    try:
        return await svc.run_evaluation(db=db, request=body)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{evaluation_run_id}", response_model=EvaluationStatusResponse)
async def get_evaluation_status(
    evaluation_run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationStatusResponse:
    try:
        return await svc.get_evaluation(db=db, evaluation_run_id=evaluation_run_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{evaluation_run_id}/report",
    response_model=EvaluationReportResponse,
)
async def get_evaluation_report(
    evaluation_run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationReportResponse:
    try:
        return await svc.get_report(db=db, evaluation_run_id=evaluation_run_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{evaluation_run_id}/report.md", response_class=PlainTextResponse)
async def get_evaluation_report_markdown(
    evaluation_run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> str:
    try:
        report = await svc.get_report(db=db, evaluation_run_id=evaluation_run_id)
        return report.markdown
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
