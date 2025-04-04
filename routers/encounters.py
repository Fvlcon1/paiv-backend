# routers/encounters.py
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import uuid
import logging
import time
from tempfile import SpooledTemporaryFile
import asyncio

from db import User, VerificationToken, RecentVisit, Disposition
from schemas import InitializeVerificationRequest
from dependencies import get_db, get_current_user
from security import decode_access_token
from utils import FaceComparisonSystem
from storage import upload_to_s3, generate_s3_key

router = APIRouter(prefix="/encounter", tags=["Encounters"])
logger = logging.getLogger(__name__)
face_system = FaceComparisonSystem()

# --- Initialize Encounter ---
@router.post("/initiate")
def initialize_verification(
    request_data: InitializeVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        member = db.query(VerificationToken).filter(
            VerificationToken.membership_id == request_data.membership_id
        ).order_by(VerificationToken.created_at.desc()).first()

        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        token_id = uuid.uuid4()
        token_string = str(uuid.uuid4())

        verification_token = VerificationToken(
            id=token_id,
            token=token_string,
            membership_id=member.membership_id,
            nhis_number=member.nhis_number,
            user_id=current_user.id,
            gender=member.gender,
            date_of_birth=member.date_of_birth,
            profile_image_url=member.profile_image_url,
            first_name=member.first_name,
            middle_name=member.middle_name,
            last_name=member.last_name,
            current_expiry_date=member.current_expiry_date,
            enrolment_status=member.enrolment_status,
            phone_number=member.phone_number,
            ghana_card_number=member.ghana_card_number,
            residential_address=member.residential_address,
            insurance_type=member.insurance_type,
        )

        visit = RecentVisit.create_from_member(member)
        visit.user_id = current_user.id

        db.add(verification_token)
        db.add(visit)
        db.commit()

        return {
            "status": "success",
            "token": token_string,
            "member_info": {
                "membership_id": member.membership_id,
                "name": f"{member.first_name} {member.last_name}",
                "nhis_number": member.nhis_number,
                "expiry_date": member.current_expiry_date
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error initializing verification: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error initializing encounter")

# --- Upload and Compare ---
@router.post("/compare")
async def compare_images(
    webcam_image: UploadFile = File(...),
    verification_token_str: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        token = db.query(VerificationToken).filter(
            VerificationToken.token == verification_token_str
        ).first()

        if not token:
            raise HTTPException(status_code=404, detail="Verification token not found")

        file_content = await webcam_image.read()
        await webcam_image.seek(0)

        comparison_result = await face_system.compare_blobs(
            token.profile_image_url, webcam_image
        )

        is_verified = comparison_result["match_summary"]["is_match"]
        confidence = float(comparison_result["match_summary"]["confidence"])

        s3_key = generate_s3_key(str(current_user.id))
        temp_file = SpooledTemporaryFile()
        temp_file.write(file_content)
        temp_file.seek(0)

        image_url = await upload_to_s3(temp_file, s3_key)

        token.verification_status = is_verified
        token.final_verification_status = is_verified
        token.compare_image_url = image_url
        db.commit()

        return {
            "status": "success",
            "match": is_verified,
            "confidence": confidence,
            "image_url": image_url
        }

    except Exception as e:
        logger.error(f"Comparison failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error comparing face images")

# --- Finalize Encounter ---
@router.post("/finalize")
async def finalize_encounter(
    token_id: str = Form(...),
    webcam_image: UploadFile = File(...),
    disposition_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        token = db.query(VerificationToken).filter(
            VerificationToken.token == token_id
        ).first()

        if not token:
            raise HTTPException(status_code=404, detail="Verification token not found")
        if token.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized user")

        disposition = db.query(Disposition).filter(Disposition.id == disposition_id).first()
        if not disposition:
            raise HTTPException(status_code=400, detail="Invalid disposition ID")

        file_content = await webcam_image.read()
        await webcam_image.seek(0)

        comparison_result = await face_system.compare_blobs(
            token.profile_image_url, webcam_image
        )

        is_verified = comparison_result["match_summary"]["is_match"]
        s3_key = f"encounter/{current_user.id}/{int(time.time())}.jpg"
        temp_file = SpooledTemporaryFile()
        temp_file.write(file_content)
        temp_file.seek(0)

        image_url = await upload_to_s3(temp_file, s3_key)

        token.disposition_name = disposition.name
        token.final_verification_status = is_verified
        token.final_time = datetime.utcnow()
        token.encounter_image_url = image_url

        db.commit()
        db.refresh(token)

        return {
            "status": "success",
            "message": "Encounter finalized",
            "disposition": disposition.name,
            "verified": is_verified,
            "image_url": image_url
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error finalizing encounter: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to finalize encounter")
