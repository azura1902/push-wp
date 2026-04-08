from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.keyword import Keyword
from app.schemas import KeywordCreate, KeywordRead

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.get("/", response_model=list[KeywordRead])
def list_keywords(db: Session = Depends(get_db)):
    return db.query(Keyword).order_by(Keyword.id.desc()).all()


@router.post("/", response_model=KeywordRead, status_code=201)
def create_keyword(payload: KeywordCreate, db: Session = Depends(get_db)):
    kw = Keyword(**payload.model_dump())
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return kw


@router.get("/{kw_id}", response_model=KeywordRead)
def get_keyword(kw_id: int, db: Session = Depends(get_db)):
    kw = db.get(Keyword, kw_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return kw


@router.delete("/{kw_id}", status_code=204)
def delete_keyword(kw_id: int, db: Session = Depends(get_db)):
    kw = db.get(Keyword, kw_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(kw)
    db.commit()
