# routers/visits.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from db import RecentVisit, User, SessionLocal
from schemas import RecentVisit as RecentVisitSchema
from dependencies import get_db, get_current_user

router = APIRouter(prefix="/recent-visits", tags=["Recent Visits"])
logger = logging.getLogger(__name__)

# --- Get all visits with pagination ---
@router.get("/", response_model=List[RecentVisitSchema])
def get_recent_visits(
    skip: int = 0,
    limit: int = 15,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        visits = (
            db.query(RecentVisit)
            .order_by(RecentVisit.visit_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return visits
    except Exception as e:
        logger.error(f"Error retrieving recent visits: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving recent visits")

# --- Get visits for current user only ---
@router.get("/my", response_model=List[RecentVisitSchema])
def get_my_visits(
    skip: int = 0,
    limit: int = 15,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        query = db.query(RecentVisit).filter(RecentVisit.user_id == current_user.id)

        if from_date:
            query = query.filter(RecentVisit.visit_date >= from_date)
        if to_date:
            query = query.filter(RecentVisit.visit_date <= to_date)

        visits = query.order_by(RecentVisit.visit_date.desc()).offset(skip).limit(limit).all()
        return visits
    except Exception as e:
        logger.error(f"Error retrieving user's visits: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving user-specific visits")

# --- Get single visit ---
@router.get("/{visit_id}", response_model=RecentVisitSchema)
def get_visit(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        visit = db.query(RecentVisit).filter(RecentVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")
        return visit
    except Exception as e:
        logger.error(f"Error retrieving visit by ID: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving visit")

# --- Delete visit ---
@router.delete("/{visit_id}", response_model=dict)
def delete_visit(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        visit = db.query(RecentVisit).filter(RecentVisit.id == visit_id).first()
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")

        if visit.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to delete this visit")

        db.delete(visit)
        db.commit()
        return {"message": "Visit deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting visit: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting visit")
