import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.database import get_db
from app.models.auth import CoupleProfile, LocalAuth

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str
    gender: str = "N"

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r'^[a-z0-9_]{4,20}$', v):
            raise ValueError("아이디는 4~20자 영문 소문자, 숫자, _만 가능합니다.")
        if v[0].isdigit():
            raise ValueError("아이디는 숫자로 시작할 수 없습니다.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError("비밀번호는 영문자를 포함해야 합니다.")
        if not re.search(r'[0-9]', v):
            raise ValueError("비밀번호는 숫자를 포함해야 합니다.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    nickname: str
    gender: str


class MeResponse(BaseModel):
    user_id: str
    username: str
    nickname: str
    gender: str


def get_current_user(
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> MeResponse:
    if not cred:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    payload = decode_token(cred.credentials)
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="토큰이 만료됐거나 유효하지 않습니다.")

    auth = db.query(LocalAuth).filter(LocalAuth.username == payload["sub"]).first()
    if not auth:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")

    return MeResponse(
        user_id=auth.user_id,
        username=auth.username,
        nickname=auth.nickname,
        gender=auth.gender,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(LocalAuth).filter(LocalAuth.username == body.username).first():
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")

    user_id = str(uuid.uuid4())
    auth = LocalAuth(
        id=str(uuid.uuid4()),
        username=body.username,
        password_hash=hash_password(body.password),
        user_id=user_id,
        nickname=body.nickname,
        gender=body.gender,
    )
    db.add(auth)
    db.commit()

    return TokenResponse(
        access_token=create_access_token({"sub": body.username}),
        user_id=user_id,
        username=body.username,
        nickname=body.nickname,
        gender=body.gender,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    auth = db.query(LocalAuth).filter(LocalAuth.username == body.username).first()
    if not auth or not verify_password(body.password, auth.password_hash):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    return TokenResponse(
        access_token=create_access_token({"sub": auth.username}),
        user_id=auth.user_id,
        username=auth.username,
        nickname=auth.nickname,
        gender=auth.gender,
    )


@router.get("/me", response_model=MeResponse)
def me(current: MeResponse = Depends(get_current_user)):
    return current


# ── 두 사람 이름 ('A님·B님' 대신) ────────────────────────────────────
class ProfileBody(BaseModel):
    my_name: str = ""
    partner_name: str = ""

    @field_validator("my_name", "partner_name")
    @classmethod
    def clean(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) > 20:
            raise ValueError("이름은 20자 이하로 입력하세요.")
        return v


@router.get("/profile", response_model=ProfileBody)
def get_profile(current: MeResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    """저장된 이름. 아직 없으면 내 이름은 닉네임, 상대 이름은 빈 값"""
    row = db.get(CoupleProfile, current.user_id)
    if not row:
        return ProfileBody(my_name=current.nickname, partner_name="")
    return ProfileBody(my_name=row.my_name or current.nickname, partner_name=row.partner_name)


@router.put("/profile", response_model=ProfileBody)
def save_profile(body: ProfileBody, current: MeResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(CoupleProfile, current.user_id)
    if not row:
        row = CoupleProfile(user_id=current.user_id)
        db.add(row)
    row.my_name, row.partner_name = body.my_name, body.partner_name
    db.commit()
    return body