from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/semantic", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def semantic_search() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )
