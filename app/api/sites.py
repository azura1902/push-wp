from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.site import Site
from app.schemas import SiteCreate, SiteRead
from app.services.wp_service import WordPressClient

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("/", response_model=list[SiteRead])
def list_sites(db: Session = Depends(get_db)):
    return db.query(Site).all()


@router.post("/", response_model=SiteRead, status_code=201)
def create_site(payload: SiteCreate, db: Session = Depends(get_db)):
    site = Site(**payload.model_dump())
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/{site_id}", response_model=SiteRead)
def get_site(site_id: int, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.put("/{site_id}", response_model=SiteRead)
def update_site(site_id: int, payload: SiteCreate, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    for k, v in payload.model_dump().items():
        setattr(site, k, v)
    db.commit()
    db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=204)
def delete_site(site_id: int, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    db.delete(site)
    db.commit()


@router.post("/{site_id}/test")
def test_site_connection(site_id: int, db: Session = Depends(get_db)):
    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    client = WordPressClient(site.url, site.username, site.app_password)
    ok = client.test_connection()
    return {"connected": ok}
