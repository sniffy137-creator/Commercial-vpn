from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models.plan import Plan
from app.db.models.subscription import Subscription
from app.db.models.user import User


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AdminUserNotFoundError(Exception):
    user_id: int

    def message(self) -> str:
        return "User not found"


@dataclass
class AdminPlanNotFoundError(Exception):
    plan_code: str

    def message(self) -> str:
        return "Plan not found"


@dataclass
class AdminPlanInactiveError(Exception):
    plan_code: str

    def message(self) -> str:
        return "Plan is inactive"


class AdminSubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_or_404(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.id == user_id).one_or_none()
        if not user:
            raise AdminUserNotFoundError(user_id=user_id)
        return user

    def get_plan_by_code(self, plan_code: str) -> Plan:
        plan = self.db.query(Plan).filter(Plan.code == plan_code).one_or_none()
        if not plan:
            raise AdminPlanNotFoundError(plan_code=plan_code)
        if not plan.is_active:
            raise AdminPlanInactiveError(plan_code=plan_code)
        return plan

    def ensure_subscription_row(self, user: User) -> Subscription:
        # у тебя: 1 подписка на юзера (unique user_id)
        sub = getattr(user, "subscription", None)
        if sub is None:
            sub = Subscription(user_id=user.id, plan_id=None, status="none", expires_at=None)
            self.db.add(sub)
            self.db.commit()
            self.db.refresh(sub)
        return sub

    def grant(self, user_id: int, *, plan_code: str, expires_at: datetime | None) -> Subscription:
        user = self.get_user_or_404(user_id)
        plan = self.get_plan_by_code(plan_code)

        sub = self.ensure_subscription_row(user)

        sub.plan_id = plan.id
        sub.status = "active"
        sub.expires_at = expires_at

        self.db.commit()
        self.db.refresh(sub)
        return sub

    def extend(self, user_id: int, *, days: int) -> Subscription:
        user = self.get_user_or_404(user_id)
        sub = self.ensure_subscription_row(user)

        now = utcnow()

        # если expires_at нет -> бессрочная, продление не имеет смысла (оставляем как есть)
        if sub.expires_at is None:
            return sub

        base = sub.expires_at
        if base < now:
            base = now

        sub.expires_at = base + timedelta(days=days)
        if sub.status != "active":
            sub.status = "active"

        self.db.commit()
        self.db.refresh(sub)
        return sub

    def cancel(self, user_id: int, *, immediately: bool = True) -> Subscription:
        user = self.get_user_or_404(user_id)
        sub = self.ensure_subscription_row(user)

        sub.status = "canceled"
        if immediately:
            sub.expires_at = utcnow()

        self.db.commit()
        self.db.refresh(sub)
        return sub

    def reactivate(self, user_id: int) -> Subscription:
        user = self.get_user_or_404(user_id)
        sub = self.ensure_subscription_row(user)

        # можно реактивировать только если есть план
        if sub.plan_id is None:
            # оставим как есть: админ должен сначала grant
            return sub

        sub.status = "active"
        self.db.commit()
        self.db.refresh(sub)
        return sub
