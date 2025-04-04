# routers/claims.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import uuid
import logging

from db import SessionLocal, Claim, VerificationToken, User
from schemas import ClaimCreate, ClaimResponse
from security import decode_access_token
from dependencies import get_current_user, get_db

router = APIRouter(prefix="/claims", tags=["Claims"])
logger = logging.getLogger(__name__)

# --- Create Claim ---
@router.post("/submit", response_model=ClaimResponse)
def submit_claim(
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        verification = db.query(VerificationToken).filter(
            VerificationToken.token == claim_data.encounter_token
        ).first()

        if not verification:
            raise HTTPException(status_code=404, detail="Invalid encounter token")

        patient_name = f"{verification.first_name} {verification.middle_name or ''} {verification.last_name}".strip()
        drugs_list = [{"code": d.code, "dosage": d.dosage} for d in claim_data.drugs]

        new_claim = Claim(
            id=uuid.uuid4(),
            encounter_token=claim_data.encounter_token,
            diagnosis=claim_data.diagnosis,
            service_type=claim_data.service_type,
            drugs=drugs_list,
            medical_procedures=claim_data.medical_procedures,
            lab_tests=claim_data.lab_tests,
            created_at=datetime.utcnow(),
            user_id=current_user.id,
            status="pending",
            reason=None,
            adjusted_amount=None,
            total_payout=None,
            patient_name=patient_name,
            hospital_name=current_user.hospital_name,
            location=current_user.location.get("address", "Unknown")
        )

        db.add(new_claim)
        db.commit()
        db.refresh(new_claim)

        return new_claim

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting claim: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during claim submission")

# --- Get Claims ---
@router.get("/", response_model=List[ClaimResponse])
def get_claims(
    user_id: Optional[int] = Query(None),
    encounter_token: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        query = db.query(Claim)

        if user_id:
            query = query.filter(Claim.user_id == user_id)
        if encounter_token:
            query = query.filter(Claim.encounter_token == encounter_token)
        if start_date:
            query = query.filter(Claim.created_at >= start_date)
        if end_date:
            query = query.filter(Claim.created_at <= end_date)

        claims = query.order_by(Claim.created_at.desc()).offset(offset).limit(limit).all()
        return claims
    except Exception as e:
        logger.error(f"Error retrieving claims: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during claim retrieval")
