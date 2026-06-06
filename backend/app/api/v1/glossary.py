from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.glossary import glossary_manager

router = APIRouter()


class GlossaryPayload(BaseModel):
    source: str
    target: str
    note: str = ""


@router.get("")
async def list_glossary() -> list[dict]:
    return [entry.__dict__ for entry in glossary_manager.list_entries()]


@router.post("")
async def create_glossary(payload: GlossaryPayload, db: Session = Depends(get_db)) -> dict:
    entry = glossary_manager.add_entry_db(db, payload.source, payload.target, payload.note)
    return entry.__dict__


@router.put("/{source}")
async def update_glossary(source: str, payload: GlossaryPayload, db: Session = Depends(get_db)) -> dict:
    if source.lower() != payload.source.lower():
        deleted = glossary_manager.delete_entry_db(db, source)
        if not deleted:
            raise HTTPException(status_code=404, detail="Glossary entry not found")
        entry = glossary_manager.add_entry_db(db, payload.source, payload.target, payload.note)
        return entry.__dict__

    entry = glossary_manager.update_entry_db(db, source, payload.target, payload.note)
    if not entry:
        raise HTTPException(status_code=404, detail="Glossary entry not found")
    return entry.__dict__


@router.delete("/{source}")
async def delete_glossary(source: str, db: Session = Depends(get_db)) -> dict:
    ok = glossary_manager.delete_entry_db(db, source)
    if not ok:
        raise HTTPException(status_code=404, detail="Glossary entry not found")
    return {"ok": True}
