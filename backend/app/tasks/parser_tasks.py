"""Celery task for repository preparation and parsing (indexing_cpu queue)."""

import asyncio
import logging
from uuid import UUID, uuid4

from celery import Task

from app.core.celery_app import celery_app
from app.db.session import WorkerSessionLocal as SessionLocal
from app.execution.failure_engine import handle_parser_failure
from app.execution.parser_engine import (
    cleanup_incomplete_staged_rows,
    final_parser_checkpoint,
    get_ephemeral_workspace_path,
    claim_parser_stage_lease,
    resolve_and_freeze_commit_sha,
    transition_preparing_to_parsing,
)
from app.services.git_service import GitService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.parser_tasks.task_prepare_and_parse",
    queue="indexing_cpu",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=6600,
    time_limit=7200,
)
def task_prepare_and_parse(self: Task, generation_id_str: str) -> dict:
    """Task to prepare workspace, resolve commit SHA, parse repo AST/symbols/chunks under stage lease fencing."""
    task_id = self.request.id or str(uuid4())
    generation_id = UUID(generation_id_str)

    return asyncio.run(_async_prepare_and_parse(generation_id, task_id))


async def _async_prepare_and_parse(generation_id: UUID, task_id: str) -> dict:
    git_svc = GitService()

    async with SessionLocal() as db:
        # 1. Atomic lease claim
        claim = await claim_parser_stage_lease(db, generation_id, task_id)
        if not claim:
            logger.info("Parser lease claim skipped for generation %s (not desired or active lease)", generation_id)
            await db.commit()
            return {"status": "skipped", "reason": "claim_failed_or_not_desired"}

        stage_attempt = claim["stage_attempt"]
        requested_ref = claim["requested_ref"]
        current_commit_sha = claim["commit_sha"]
        embedding_backend = claim["embedding_backend"]

        try:
            # 2. Retry cleanup if taking over an expired attempt
            if stage_attempt > 1:
                await cleanup_incomplete_staged_rows(db, generation_id, task_id, stage_attempt)
                await db.commit()

            # 3. Resolve & freeze commit SHA
            # Note: For workspace path, use resolved or pending sha
            placeholder_path = get_ephemeral_workspace_path(generation_id, current_commit_sha or requested_ref)
            commit_sha = await resolve_and_freeze_commit_sha(
                db=db,
                generation_id=generation_id,
                task_id=task_id,
                claimed_attempt=stage_attempt,
                git_service=git_svc,
                repo_path=placeholder_path,
                requested_ref=requested_ref,
                current_commit_sha=current_commit_sha,
            )
            await db.commit()

            # 4. Transition preparing -> parsing under fence
            await transition_preparing_to_parsing(db, generation_id, task_id, stage_attempt)
            await db.commit()

            # 5. Parse repository files & generate chunks
            from pathlib import Path
            from sqlalchemy import select
            from app.db.models import CodeChunk, Repository
            from app.services.indexing_service import IndexingService

            chunks_stmt = select(CodeChunk).where(CodeChunk.generation_id == generation_id)
            chunks_res = await db.execute(chunks_stmt)
            chunks = list(chunks_res.scalars().all())

            if not chunks:
                repo_stmt = select(Repository).where(Repository.id == claim["repository_id"])
                repo_res = await db.execute(repo_stmt)
                repo_obj = repo_res.scalars().first()

                if repo_obj and repo_obj.local_path:
                    idx_svc = IndexingService(git_service=git_svc)
                    actual_repo_path = Path(repo_obj.local_path)
                    if actual_repo_path.exists():
                        git_repo = git_svc.open_repository(actual_repo_path)
                        if requested_ref:
                            try:
                                git_svc.checkout_ref(git_repo, requested_ref)
                            except Exception:
                                pass

                        tracked_files = git_svc.list_tracked_files(git_repo)
                        parsed_files = []
                        file_contents = {}
                        code_files_by_path = {}
                        symbol_records_by_key = {}

                        from app.analysis.languages import Language
                        from app.core.config import settings
                        from app.db.models import CodeFile, Symbol
                        from app.utils.hashing import compute_normalized_hash

                        from app.services.progress_publisher import ProgressStreamPublisher
                        import time
                        publisher = ProgressStreamPublisher()
                        total_files = len(tracked_files)
                        parsing_start_time = time.monotonic()

                        for idx, tracked_path in enumerate(tracked_files, start=1):
                            if idx % 10 == 0 or idx == total_files:
                                elapsed = time.monotonic() - parsing_start_time
                                files_per_sec = idx / max(0.1, elapsed)
                                rem_files = max(0, total_files - idx)
                                parsing_rem_sec = rem_files / files_per_sec
                                est_chunks = total_files * 10
                                est_batches = max(1, est_chunks // 16)
                                total_eta = int(parsing_rem_sec + (est_batches * 4.0))

                                await publisher.publish_progress(
                                    generation_id=generation_id,
                                    payload={
                                        "status": "indexing",
                                        "phase": "parsing",
                                        "phase_name": f"Parsing files ({idx}/{total_files})",
                                        "files_total": total_files,
                                        "files_processed": idx,
                                        "progress_percentage": round(min(45.0, (idx / max(1, total_files)) * 45.0), 1),
                                        "estimated_seconds_remaining": total_eta,
                                    },
                                )

                            full_path = actual_repo_path / tracked_path
                            if idx_svc._should_skip_path(full_path, tracked_path):
                                continue
                            content_bytes = full_path.read_bytes()
                            if git_svc.is_binary_file(content=content_bytes):
                                continue
                            content = content_bytes.decode("utf-8", errors="replace")
                            classification = idx_svc.classifier.classify(tracked_path, content)
                            if (
                                classification["should_ignore"]
                                or classification["is_generated"]
                                or not classification["is_supported"]
                            ):
                                continue

                            parsed = idx_svc._parse_file(
                                tracked_path,
                                content,
                                classification["language"],
                            )
                            code_file = CodeFile(
                                repository_id=claim["repository_id"],
                                generation_id=generation_id,
                                path=Path(tracked_path).as_posix(),
                                language=str(
                                    classification["language"].value
                                    if isinstance(classification["language"], Language)
                                    else classification["language"]
                                ),
                                content_hash=compute_normalized_hash(content),
                                loc=int(classification["loc"]),
                                is_test=bool(classification["is_test"]),
                                is_generated=bool(classification["is_generated"]),
                                last_seen_commit=commit_sha,
                                file_metadata={},
                            )
                            code_files_by_path[tracked_path] = code_file
                            parsed_files.append(parsed)
                            file_contents[tracked_path] = content

                        if code_files_by_path:
                            await idx_svc._upsert_code_files(db, list(code_files_by_path.values()))
                            await idx_svc._save_symbols(
                                db,
                                claim["repository_id"],
                                parsed_files,
                                code_files_by_path,
                                symbol_records_by_key,
                                generation_id=generation_id,
                            )
                            _, chunks = await idx_svc._save_chunks(
                                db,
                                claim["repository_id"],
                                parsed_files,
                                code_files_by_path,
                                symbol_records_by_key,
                                file_contents,
                                generation_id=generation_id,
                            )
                            edges = idx_svc.graph_builder.build_edges(
                                parsed_files, set(code_files_by_path)
                            )
                            await idx_svc._save_dependency_edges(
                                db,
                                claim["repository_id"],
                                edges,
                                code_files_by_path,
                                generation_id=generation_id,
                            )
                            await idx_svc._save_commit_metadata(
                                db,
                                claim["repository_id"],
                                git_repo,
                                settings.MAX_COMMITS_TO_MINE,
                            )
                            await db.flush()

                            est_batches = max(1, len(chunks) // max(1, settings.EMBEDDING_BATCH_SIZE))
                            est_eta = int(est_batches * 4.0)

                            await publisher.publish_progress(
                                generation_id=generation_id,
                                payload={
                                    "status": "indexing",
                                    "phase": "parsing",
                                    "phase_name": f"Parsing complete ({len(code_files_by_path)} files, {len(chunks)} chunks)",
                                    "files_total": total_files,
                                    "files_processed": total_files,
                                    "chunks_total": len(chunks),
                                    "chunks_processed": 0,
                                    "progress_percentage": 50.0,
                                    "estimated_seconds_remaining": est_eta,
                                },
                            )

            # 6. Final parser checkpoint
            checkpoint_res = await final_parser_checkpoint(
                db=db,
                generation_id=generation_id,
                task_id=task_id,
                claimed_attempt=stage_attempt,
                chunks=chunks,
                embedding_backend=embedding_backend,
            )
            await db.commit()
            return {"status": "success", "stage_attempt": stage_attempt, "commit_sha": commit_sha, **checkpoint_res}

        except Exception as exc:
            logger.exception("Error in task_prepare_and_parse for generation %s: %s", generation_id, exc)
            await db.rollback()
            # Fenced terminal failure handling
            async with SessionLocal() as fail_db:
                fail_status = await handle_parser_failure(
                    db=fail_db,
                    generation_id=generation_id,
                    task_id=task_id,
                    stage_attempt=stage_attempt,
                    error_message=str(exc),
                )
                await fail_db.commit()
            raise exc
