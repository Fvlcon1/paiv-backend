import uuid
import datetime
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Index, Integer, Boolean, JSON, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from databases import Database
from sqlalchemy.dialects.postgresql import UUID, ARRAY


# Database URL
DATABASE_URL = "postgresql://neondb_owner:npg_Emq9gohbK8se@ep-yellow-dust-a45jsws7-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Database setup
database = Database(DATABASE_URL)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Claim(Base):
    __tablename__ = "claims"
    
    encounter_token = Column(String, ForeignKey('verification_tokens.token'), primary_key=True, nullable=False, index=True)
    diagnosis = Column(String, nullable=False)  
    service_type = Column(ARRAY(String), nullable=False)  
    drugs = Column(JSON, nullable=False)  
    medical_procedures = Column(ARRAY(String), nullable=False)  
    lab_tests = Column(ARRAY(String), nullable=True)  
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  

    # New Fields
    status = Column(String, nullable=False, default="pending")  # 'approved', 'flagged', 'rejected'
    reason = Column(String, nullable=True)  # Reason for flag/rejection
    adjusted_amount = Column(Float, nullable=True)  # Adjusted NHIS payout after review
    total_payout = Column(Float, nullable=True)  # Original total payout requested
    
    # Additional Fields
    patient_name = Column(String, nullable=False)  # Patient's name
    hospital_name = Column(String, nullable=False)  # Hospital name
    location = Column(String, nullable=False)  # Location of the hospital

    # Relationships
    verification_token = relationship("VerificationToken", backref="claims")
    user = relationship("User", backref="submitted_claims")

    # Indexes
    __table_args__ = (
        Index('idx_claim_encounter', 'encounter_token'),
        Index('idx_claim_created_date', 'created_at'),
        Index('idx_claim_status', 'status'),
    )



class ClaimDraft(Base):
    __tablename__ = "claim_drafts"
    
    encounter_token = Column(String, ForeignKey('verification_tokens.token'), primary_key=True, nullable=False, index=True)
    diagnosis = Column(String, nullable=True)  
    service_type = Column(ARRAY(String), nullable=True)  
    drugs = Column(JSON, nullable=True)  
    medical_procedures = Column(ARRAY(String), nullable=True)  
    lab_tests = Column(ARRAY(String), nullable=True)  
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  

    # New Fields
    status = Column(String, nullable=True, default="pending")  # 'approved', 'flagged', 'rejected'
    reason = Column(String, nullable=True)  # Reason for flag/rejection
    adjusted_amount = Column(Float, nullable=True)  # Adjusted NHIS payout after review
    total_payout = Column(Float, nullable=True)  # Original total payout requested
    
    # Additional Fields
    patient_name = Column(String, nullable=True)  # Patient's name
    hospital_name = Column(String, nullable=True)  # Hospital name
    location = Column(String, nullable=True)  # Location of the hospital

    # Relationships
    verification_token = relationship("VerificationToken", backref="claim_drafts")
    user = relationship("User", backref="drafted_claims")

    # Indexes
    __table_args__ = (
        Index('idx_claim_draft_encounter', 'encounter_token'),
        Index('idx_claim_draft_created_date', 'created_at'),
        Index('idx_claim_draft_status', 'status'),
    )

    

class ClaimNotification(Base):
    __tablename__ = "claim_notifications"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, unique=True, index=True)  # "approved", "rejected", etc.
    count = Column(Integer, default=0)
    

class Disposition(Base):
    __tablename__ = "dispositions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=False)

class Medicines(Base):
    __tablename__ = "medicines"

    code = Column(String(50), primary_key=True, index=True)  # Use 'code' as the primary key
    generic_name = Column(String, nullable=False)
    unit_of_pricing = Column(String(100), nullable=False)
    price = Column(Float, nullable=True)
    level_of_prescribing = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class ServiceTariffs(Base):
    __tablename__ = "service_tariffs"

    code = Column(String(50), primary_key=True, index=True)  # Use 'code' as the primary key
    service = Column(String, nullable=False)
    tariff = Column(Float, nullable=False)  # Tariff in GH₵
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hospital_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    location = Column(JSON, nullable=False)  # Store location as JSON

    # Fields for 2FA
    totp_secret = Column(String, nullable=True)  # Store the TOTP secret key
    backup_codes = Column(JSON, nullable=True)  # Store backup codes as a JSON array
    is_2fa_enabled = Column(Boolean, default=False, nullable=False)  # Track if any 2FA is enabled
    is_email_2fa_enabled = Column(Boolean, default=False, nullable=False)  # Track if email 2FA is enabled




class EmailTwoFactor(Base):
    __tablename__ = "email_two_factor"

    id = Column(Integer, primary_key=True, index=True)  # Unique ID
    email = Column(String, nullable=False, unique=True)  # Email for 2FA
    otp = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)  # OTP creation time
    expires_at = Column(DateTime, nullable=False)  # Expiry time (2 min)



class Member(Base):
    __tablename__ = "members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    membership_id = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    gender = Column(String, nullable=False)
    marital_status = Column(String, nullable=False)
    nhis_number = Column(String, unique=True, nullable=False, index=True)
    insurance_type = Column(String, nullable=False)
    issue_date = Column(DateTime, nullable=False)
    enrolment_status = Column(String, nullable=False, index=True)
    current_expiry_date = Column(DateTime, nullable=False)
    mobile_phone_number = Column(String, nullable=False)
    residential_address = Column(String, nullable=False)
    ghana_card_number = Column(String, unique=True, nullable=False, index=True)
    profile_image_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Composite index for name search
    __table_args__ = (
        Index('idx_member_names', 'first_name', 'middle_name', 'last_name'),
    )


class VerificationToken(Base):
    __tablename__ = "verification_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    token = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    membership_id = Column(String, ForeignKey('members.membership_id'), nullable=False, index=True)
    nhis_number = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(DateTime, nullable=False)  # Added from RecentVisit
    profile_image_url = Column(String, nullable=False)  # Added from RecentVisit
    compare_image_url = Column(String, nullable=True)
    encounter_image_url = Column(String, nullable=True)
    gender = Column(String, nullable=False)  # Added from RecentVisit
    phone_number = Column(String, nullable=True)
    ghana_card_number = Column(String, nullable=True, index=True)
    residential_address = Column(String, nullable=False)
    enrolment_status = Column(String, nullable=False, index=True)  # Added from RecentVisit
    verification_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    verification_status = Column(Boolean, nullable=True, index=True)  # True if verified, False if failed
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)  # Track which user verified
    current_expiry_date = Column(DateTime, nullable=False)
    final_verification_status = Column(Boolean, nullable=True, index=True)
    disposition_name = Column(String, ForeignKey('dispositions.name'), nullable=True)
    final_time = Column(DateTime, nullable=True)
    insurance_type = Column(String, nullable=False)
 
    # Relationships
    member = relationship("Member", backref="verification_tokens")
    user = relationship("User", backref="verifications_performed")
    disposition = relationship("Disposition")

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_verification_date_range', 'verification_date', 'created_at'),
        Index('idx_user_verifications', 'user_id'),
        Index('idx_verification_status', 'verification_status'),
        Index('idx_final_verification_status', 'final_verification_status'),
        Index('idx_disposition_name', 'disposition_name'),
        Index('idx_final_time', 'final_time')  # Fixed typo "idx_final_timme"
    )
    
    @classmethod
    def create_from_member(cls, member, verification_status, user_id, disposition_name=None, final_time=None):
        """
        Create a verification token record from a member instance.
        """
        return cls(
            membership_id=member.membership_id,
            nhis_number=member.nhis_number,
            first_name=member.first_name,
            middle_name=member.middle_name,
            last_name=member.last_name,
            date_of_birth=member.date_of_birth,  # Added from RecentVisit
            profile_image_url=member.profile_image_url,  # Added from RecentVisit
            compare_image_url=compare_image_url,
            encounter_image_url=encounter_image_url,
            gender=member.gender,  # Added from RecentVisit
            enrolment_status=member.enrolment_status,  # Added from RecentVisit
            verification_status=verification_status,
            user_id=user_id,
            current_expiry_date=member.current_expiry_date,
            disposition_name=disposition_name,
            final_verification_status=None,
            final_time=final_time,
            phone_number=member.phone_number,  # ✅ Added
            ghana_card_number=member.ghana_card_number,  # ✅ Added
            residential_address=member.residential_address,  # ✅ Added
            insurance_type=member.insurance_type  # ✅ Added
        )











class RecentVisit(Base):
    __tablename__ = "recent_visits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    membership_id = Column(String, ForeignKey('members.membership_id'), nullable=False, index=True)
    nhis_number = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    profile_image_url = Column(String, nullable=False)
    visit_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    gender = Column(String, nullable=False)
    enrolment_status = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # New: Link to VerificationToken
    verification_token_id = Column(UUID(as_uuid=True), ForeignKey('verification_tokens.id'), nullable=True, index=True)

    # Relationships
    member = relationship("Member", backref="visits")
    user = relationship("User", backref="recorded_visits")
    verification_token = relationship("VerificationToken", backref="recent_visits")

    # Index for efficient querying
    __table_args__ = (
        Index('idx_visit_date_range', 'visit_date', 'membership_id'),
        Index('idx_user_visits', 'user_id'),
    )
    
    @classmethod
    def create_from_member(cls, member, verification_token_id=None):
        """
        Create a visit record from a member instance, optionally linking a verification token.
        """
        return cls(
            membership_id=member.membership_id,
            nhis_number=member.nhis_number,
            first_name=member.first_name,
            middle_name=member.middle_name,
            last_name=member.last_name,
            date_of_birth=member.date_of_birth,
            profile_image_url=member.profile_image_url,
            gender=member.gender,
            enrolment_status=member.enrolment_status,
            verification_token_id=verification_token_id  # Store the token ID
        )


# Function to initialize the database
def init_db():
    Base.metadata.create_all(bind=engine)


# Initialize the database and create both tables
init_db()


# Helper function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
