from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health() -> dict[str, str]: #1254235
    return {"status": "ok"}  # 12431325
