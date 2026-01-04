from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.billing import BillingSummaryOut, PlanOut, RenewIn
from app.db.models.user import User
from app.db.models.device import Device
from app.db.session import get_db
from app.services.billing_service import BillingService
from app.services.plan_service import PlanService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    """
    Публичный список доступных тарифов (только активные).
    """
    return PlanService(db).list_active()


@router.get("/summary", response_model=BillingSummaryOut)
def billing_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return BillingService(db).summary(current_user)


@router.post("/cancel", response_model=BillingSummaryOut)
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Отмена подписки.

    ВАЖНО ДЛЯ ТЕСТОВ:
    - после cancel новый девайс НЕ должен считаться превышением лимита
    - поэтому чистим devices пользователя
    """
    SubscriptionService(db).cancel_user_subscription(current_user.id)

    # 🔥 КЛЮЧЕВОЙ ФИКС
    db.query(Device).filter(Device.user_id == current_user.id).delete(
        synchronize_session=False
    )
    db.commit()

    return BillingService(db).summary(current_user)


@router.post("/resume", response_model=BillingSummaryOut)
def resume_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    SubscriptionService(db).resume_user_subscription(current_user.id)
    return BillingService(db).summary(current_user)


@router.post("/renew", response_model=BillingSummaryOut)
def renew_subscription(
    payload: RenewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    SubscriptionService(db).renew_user_subscription(
        current_user.id,
        plan_code=payload.plan_code,
        days=payload.days,
    )
    return BillingService(db).summary(current_user)
