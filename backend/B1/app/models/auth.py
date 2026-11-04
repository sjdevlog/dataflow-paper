from sqlalchemy import Column, String, DateTime
from app.database import Base
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

class LocalAuth(Base):
    __tablename__ = "local_auth"

    id           = Column(String, primary_key=True)  # uuid4 문자열
    username     = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    user_id      = Column(String, unique=True, nullable=False)
    nickname     = Column(String(50), nullable=False)
    gender       = Column(String(10), nullable=False, default="N")
    created_at   = Column(DateTime, default=utcnow)


class CoupleProfile(Base):
    """두 사람 이름 — 'A님·B님' 대신 화면에 쓸 이름 (계정당 1개)"""
    __tablename__ = "couple_profile"

    user_id      = Column(String, primary_key=True)          # local_auth.user_id
    my_name      = Column(String(20), nullable=False, default="")
    partner_name = Column(String(20), nullable=False, default="")
    updated_at   = Column(DateTime, default=utcnow, onupdate=utcnow)
