from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models.plan import Plan
from app.db.models.subscription import Subscription


@dataclass
class SubscriptionExpiredError(Exception):
    def message(self) -> str:
        return "Subscription is expired and cannot be resumed"


@dataclass
class SubscriptionNotFoundError(Exception):
    def message(self) -> str:
        return "Subscription not found"


@dataclass
class PlanNotFoundError(Exception):
    plan_code: str

    def message(self) -> str:
        return f"Plan not found: {self.plan_code}"


@dataclass
class PlanInactiveError(Exception):
    plan_code: str

    def message(self) -> str:
        return f"Plan is inactive: {self.plan_code}"


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_user_has_subscription(self, user_id: int) -> Subscription:
        """
        Variant C: любой user должен иметь subscription (хотя бы FREE).
        """
        existing = self.db.query(Subscription).filter(Subscription.user_id == user_id).one_or_none()
        if existing:
            return existing

        free_plan = self.db.query(Plan).filter(Plan.code == "free").one()

        sub = Subscription(
            user_id=user_id,
            plan_id=free_plan.id,
            status="active",
            expires_at=None,
        )
        self.db.add(sub)
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def get_subscription(self, user_id: int) -> Subscription:
        sub = self.db.query(Subscription).filter(Subscription.user_id == user_id).one_or_none()
        if not sub:
            raise SubscriptionNotFoundError()
        return sub

    def get_active_subscription(self, user_id: int) -> Subscription | None:
        """
        Единственная "истина" активной подписки:
        - status == active
        - expires_at is None OR expires_at > now(UTC)
        """
        sub = self.db.query(Subscription).filter(Subscription.user_id == user_id).one_or_none()
        if not sub:
            return None

        if sub.status != "active":
            return None

        now = datetime.now(timezone.utc)
        if sub.expires_at is not None and sub.expires_at <= now:
            return None

        return sub

    def cancel_user_subscription(self, user_id: int) -> Subscription:
        """
        Cancel = делаем подписку неактивной немедленно.
        """
        sub = self.get_subscription(user_id)
        sub.status = "canceled"
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def resume_user_subscription(self, user_id: int) -> Subscription:
        """
        Resume возможно только если подписка НЕ истекла по expires_at.
        Если expires_at в прошлом — нужен renew.
        """
        sub = self.get_subscription(user_id)

        now = datetime.now(timezone.utc)
        if sub.expires_at is not None and sub.expires_at <= now:
            raise SubscriptionExpiredError()

        sub.status = "active"
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def renew_user_subscription(self, user_id: int, *, plan_code: str, days: int = 30) -> Subscription:
        """
        Renew = установить/продлить срок подписки.
        - план выбирается по plan_code
        - expires_at продлевается от max(now, current_expires_at)
        - status становится active
        """
        if days <= 0:
            days = 30

        plan = self.db.query(Plan).filter(Plan.code == plan_code).one_or_none()
        if not plan:
            raise PlanNotFoundError(plan_code=plan_code)
        if not plan.is_active:
            raise PlanInactiveError(plan_code=plan_code)

        sub = self.get_subscription(user_id)

        now = datetime.now(timezone.utc)
        base = now
        if sub.expires_at is not None and sub.expires_at > now:
            base = sub.expires_at  # продлеваем от текущего срока, если ещё не истекла

        sub.plan_id = plan.id
        sub.status = "active"
        sub.expires_at = base + timedelta(days=days)

        self.db.commit()
        self.db.refresh(sub)
        return sub
