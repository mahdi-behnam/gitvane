from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_evaluation_service, get_repository_service, get_current_user
from app.core.errors import RepositoryNotFoundError
from app.db.models import EvaluationRun, User
from app.db.session import SessionLocal
from app.schemas.evaluation import (
    EvaluationReportResponse,
    EvaluationRunListItem,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationStatusResponse,
)
from app.services.evaluation_service import EvaluationService
from app.services.repository_service import RepositoryService

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
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvaluationRunResponse:
    try:
        await repo_svc.get_repository_or_raise(db, body.repository_id, owner_id=current_user.id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

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
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvaluationStatusResponse:
    try:
        stmt = select(EvaluationRun.repository_id).where(EvaluationRun.id == evaluation_run_id)
        result = await db.execute(stmt)
        repository_id = result.scalar_one_or_none()
        if repository_id is None:
            raise RepositoryNotFoundError(f"Evaluation run with id={evaluation_run_id} does not exist")
        
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
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
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EvaluationReportResponse:
    try:
        stmt = select(EvaluationRun.repository_id).where(EvaluationRun.id == evaluation_run_id)
        result = await db.execute(stmt)
        repository_id = result.scalar_one_or_none()
        if repository_id is None:
            raise RepositoryNotFoundError(f"Evaluation run with id={evaluation_run_id} does not exist")
        
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
        return await svc.get_report(db=db, evaluation_run_id=evaluation_run_id)
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{evaluation_run_id}/report.md", response_class=PlainTextResponse)
async def get_evaluation_report_markdown(
    evaluation_run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    svc: Annotated[EvaluationService, Depends(get_evaluation_service)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> str:
    try:
        stmt = select(EvaluationRun.repository_id).where(EvaluationRun.id == evaluation_run_id)
        result = await db.execute(stmt)
        repository_id = result.scalar_one_or_none()
        if repository_id is None:
            raise RepositoryNotFoundError(f"Evaluation run with id={evaluation_run_id} does not exist")
        
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
        report = await svc.get_report(db=db, evaluation_run_id=evaluation_run_id)
        return report.markdown
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/repository/{repository_id}/runs", response_model=list[EvaluationRunListItem])
async def list_repository_evaluation_runs(
    repository_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    repo_svc: Annotated[RepositoryService, Depends(get_repository_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[EvaluationRunListItem]:
    """Return historical evaluation runs for a repository."""
    try:
        await repo_svc.get_repository_or_raise(db, repository_id, owner_id=current_user.id)
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.repository_id == repository_id)
            .order_by(EvaluationRun.started_at.desc())
        )
        res = await db.execute(stmt)
        runs = res.scalars().all()

        return [
            EvaluationRunListItem(
                evaluation_run_id=run.id,
                name=run.name,
                status=run.status,
                commit_limit=run.commit_limit,
                methods=run.config.get("methods", []) if run.config else [],
                created_at=run.started_at.isoformat() if run.started_at else "",
            )
            for run in runs
        ]
    except RepositoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

