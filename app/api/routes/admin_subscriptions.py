from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.schemas.admin_subscription import (
    AdminCancelSubscriptionIn,
    AdminExtendSubscriptionIn,
    AdminGrantSubscriptionIn,
    AdminSubscriptionOut,
    AdminUserWithSubscriptionOut,
)
from app.db.models.user import User
from app.db.session import get_db
from app.services.admin_subscription_service import AdminSubscriptionService

router = APIRouter(
    prefix="/admin/subscriptions",
    tags=["admin-subscriptions"],
    dependencies=[Depends(require_admin)],
)


@router.get("/users", response_model=list[AdminUserWithSubscriptionOut])
def list_users_with_subscriptions(db: Session = Depends(get_db)):
    # простой список, без пагинации — ок для MVP
    users: list[User] = db.query(User).order_by(User.id.asc()).all()
    return users


@router.post("/users/{user_id}/grant", response_model=AdminSubscriptionOut)
def grant_subscription(
    user_id: int,
    payload: AdminGrantSubscriptionIn,
    db: Session = Depends(get_db),
):
    sub = AdminSubscriptionService(db).grant(
        user_id=user_id,
        plan_code=payload.plan_code,
        expires_at=payload.expires_at,
    )
    # отдаем plan_code/plan_name для UI (через relationship)
    plan = sub.plan if hasattr(sub, "plan") else None
    return {
        "user_id": sub.user_id,
        "status": sub.status,
        "plan_code": getattr(plan, "code", None),
        "plan_name": getattr(plan, "name", None),
        "expires_at": sub.expires_at,
    }


@router.post("/users/{user_id}/extend", response_model=AdminSubscriptionOut)
def extend_subscription(
    user_id: int,
    payload: AdminExtendSubscriptionIn,
    db: Session = Depends(get_db),
):
    sub = AdminSubscriptionService(db).extend(user_id=user_id, days=payload.days)
    plan = sub.plan if hasattr(sub, "plan") else None
    return {
        "user_id": sub.user_id,
        "status": sub.status,
        "plan_code": getattr(plan, "code", None),
        "plan_name": getattr(plan, "name", None),
        "expires_at": sub.expires_at,
    }


@router.post("/users/{user_id}/cancel", response_model=AdminSubscriptionOut)
def cancel_subscription(
    user_id: int,
    payload: AdminCancelSubscriptionIn,
    db: Session = Depends(get_db),
):
    sub = AdminSubscriptionService(db).cancel(user_id=user_id, immediately=payload.immediately)
    plan = sub.plan if hasattr(sub, "plan") else None
    return {
        "user_id": sub.user_id,
        "status": sub.status,
        "plan_code": getattr(plan, "code", None),
        "plan_name": getattr(plan, "name", None),
        "expires_at": sub.expires_at,
    }


@router.post("/users/{user_id}/reactivate", response_model=AdminSubscriptionOut)
def reactivate_subscription(
    user_id: int,
    db: Session = Depends(get_db),
):
    sub = AdminSubscriptionService(db).reactivate(user_id=user_id)
    plan = sub.plan if hasattr(sub, "plan") else None
    return {
        "user_id": sub.user_id,
        "status": sub.status,
        "plan_code": getattr(plan, "code", None),
        "plan_name": getattr(plan, "name", None),
        "expires_at": sub.expires_at,
    }
