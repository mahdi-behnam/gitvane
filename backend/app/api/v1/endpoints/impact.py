from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/analyze", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def analyze_impact() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.get("/runs/{analysis_run_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_impact_run(analysis_run_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )
