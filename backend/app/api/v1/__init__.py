from fastapi import APIRouter

from app.api.v1.glossary import router as glossary_router
from app.api.v1.health import router as health_router
from app.api.v1.settings import router as settings_router
from app.api.v1.transcripts import router as transcripts_router

router = APIRouter()
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(transcripts_router, prefix="/transcripts", tags=["transcripts"])
router.include_router(glossary_router, prefix="/glossary", tags=["glossary"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
