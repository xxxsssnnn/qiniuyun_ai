from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.glossary import GlossaryConflictError, glossary_manager

router = APIRouter()


class GlossaryPayload(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=255)
    note: str = Field(default="", max_length=2000)

    @field_validator("source", "target")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        return value.strip()


@router.get("")
async def list_glossary() -> list[dict]:
    return [entry.__dict__ for entry in glossary_manager.list_entries()]


@router.post("")
async def create_glossary(payload: GlossaryPayload, db: Session = Depends(get_db)) -> dict:
    try:
        entry = glossary_manager.add_entry_db(
            db,
            payload.source,
            payload.target,
            payload.note,
        )
    except GlossaryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return entry.__dict__


@router.put("/{source}")
async def update_glossary(source: str, payload: GlossaryPayload, db: Session = Depends(get_db)) -> dict:
    try:
        if (
            glossary_manager.normalize_source(source)
            != glossary_manager.normalize_source(payload.source)
        ):
            entry = glossary_manager.rename_entry_db(
                db,
                source,
                payload.source,
                payload.target,
                payload.note,
            )
        else:
            entry = glossary_manager.update_entry_db(
                db,
                source,
                payload.target,
                payload.note,
            )
    except GlossaryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not entry:
        raise HTTPException(status_code=404, detail="Glossary entry not found")
    return entry.__dict__


@router.delete("/{source}")
async def delete_glossary(source: str, db: Session = Depends(get_db)) -> dict:
    ok = glossary_manager.delete_entry_db(db, source)
    if not ok:
        raise HTTPException(status_code=404, detail="Glossary entry not found")
    return {"ok": True}
