from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_repository() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.get("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_repositories() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.get("/{repository_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_repository(repository_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.delete("/{repository_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_repository(repository_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )
