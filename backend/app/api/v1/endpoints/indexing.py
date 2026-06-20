from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/{repository_id}/index", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def index_repository(repository_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.get(
    "/{repository_id}/index/status", status_code=status.HTTP_501_NOT_IMPLEMENTED
)
async def get_index_status(repository_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )
