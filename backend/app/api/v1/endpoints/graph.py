from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get(
    "/repositories/{repository_id}/file/{file_id}/neighbors",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def get_file_neighbors(repository_id: int, file_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )


@router.get(
    "/repositories/{repository_id}/subgraph",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def get_repository_subgraph(repository_id: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint not implemented"
    )
