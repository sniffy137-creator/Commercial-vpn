from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User
from app.db.session import get_db
from app.services.device_service import DeviceIdRequiredError, DeviceService
from app.services.limits import NoActiveSubscriptionError, SubscriptionExpiredError
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    email: EmailStr


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).one_or_none()
    if exists:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Email already registered"},
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    SubscriptionService(db).ensure_user_has_subscription(user.id)

    return TokenOut(access_token=create_access_token(subject=user.email))


@router.post("/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
    x_device_name: str | None = Header(default=None, alias="X-Device-Name"),
):
    user = db.query(User).filter(User.email == form.username).one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Bad credentials"},
        )

    # ✅ тестам нужно: при валидных кредах token всегда выдаётся
    token = create_access_token(subject=user.email)

    try:
        DeviceService(db).register_or_touch_login_device(
            user=user,
            device_id=x_device_id,
            device_name=x_device_name,
        )
    except SubscriptionExpiredError:
        # ✅ expired: token выдаём, но девайс НЕ регистрируем и лимиты НЕ трогаем
        pass
    except NoActiveSubscriptionError:
        # ✅ тесты ждут body["code"] на верхнем уровне
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "code": "no_active_subscription",
                "detail": "No active subscription",
            },
        )
    except DeviceIdRequiredError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": "device_id_required",
                "detail": "X-Device-Id header required",
            },
        )

    return TokenOut(access_token=token)


@router.get("/me", response_model=MeOut)
def me(current_user: User = Depends(get_current_user)):
    return MeOut(email=current_user.email)
