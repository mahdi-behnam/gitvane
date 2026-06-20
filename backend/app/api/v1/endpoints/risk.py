from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get(
    "/repositories/{repository_id}/files", status_code=status.HTTP_501_NOT_IMPLEMENTED
)
async def get_repository_risk(repository_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )
