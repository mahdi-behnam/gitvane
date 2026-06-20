from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/run", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def run_evaluation() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.get("/{evaluation_run_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_evaluation_status(evaluation_run_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.get("/{evaluation_run_id}/report", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_evaluation_report(evaluation_run_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )
