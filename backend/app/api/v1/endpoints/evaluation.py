from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_evaluation_service
from app.core.errors import RepositoryNotFoundError
from app.db.models import EvaluationRun, Repository
from app.db.session import SessionLocal
from app.schemas.evaluation import (
    EvaluationReportResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationStatusResponse,
)
from app.services.evaluation_service import EvaluationService

router = APIRouter()


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_evaluation(
    body: EvaluationRunRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationRunResponse:
    repo_obj = await db.get(Repository, body.repository_id)
    if repo_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with id={body.repository_id} does not exist",
        )

    run = EvaluationRun(
        repository_id=body.repository_id,
        name=body.name,
        status="running",
        base_method="multiple",
        commit_limit=body.commit_limit,
        config={
            "methods": body.methods,
            "k_values": body.k_values,
            "limitation": "Uses the current indexed graph as an approximation.",
        },
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    async def async_evaluation_task() -> None:
        async with SessionLocal() as async_db:
            try:
                from app.api.deps import get_semantic_search_service
                service = EvaluationService(semantic_search_service=get_semantic_search_service())
                await service.execute_evaluation(
                    db=async_db,
                    evaluation_run_id=run.id,
                    commit_limit=body.commit_limit,
                    methods=body.methods,
                    k_values=body.k_values,
                )
            except Exception:
                pass

    background_tasks.add_task(async_evaluation_task)

    return EvaluationRunResponse(
        evaluation_run_id=run.id,
        status="running",
        summary={},
    )


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
