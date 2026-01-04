from __future__ import annotations
from typing import Union
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.device import Device
from app.db.models.plan import Plan
from app.db.models.server import Server
from app.db.models.subscription import Subscription
from app.db.models.user import User


# -------------------- domain errors --------------------

def get_active_plan_for_user(db, user_or_id: Union[int, User]):
    user_id = user_or_id.id if isinstance(user_or_id, User) else user_or_id
    user = db.query(User).filter(User.id == user_id).one()

@dataclass
class NoActiveSubscriptionError(Exception):
    def message(self) -> str:
        return "No active subscription"


@dataclass
class LimitExceededError(Exception):
    resource: str
    limit: int
    current: int

    def message(self) -> str:
        return f"Plan limit exceeded for {self.resource}"


@dataclass
class SubscriptionExpiredError(Exception):
    def message(self) -> str:
        return "Subscription expired"


# Эти ошибки у тебя импортируются из subscription_service,
# но тесты/код дергают их через handlers. Держим единый смысл.
@dataclass
class PlanNotFoundError(Exception):
    plan_code: str

    def message(self) -> str:
        return "Plan not found"


@dataclass
class PlanInactiveError(Exception):
    plan_code: str

    def message(self) -> str:
        return "Plan is inactive"


# -------------------- helpers --------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_user(db: Session, user_or_id: int | User) -> User:
    if isinstance(user_or_id, User):
        return user_or_id
    return db.query(User).filter(User.id == int(user_or_id)).one()


def _get_subscription_or_raise(user: User) -> Subscription:
    sub: Subscription | None = getattr(user, "subscription", None)
    if not sub:
        raise NoActiveSubscriptionError()

    # status "active" - единственный статус который нас интересует как активный доступ
    if sub.status != "active":
        raise NoActiveSubscriptionError()

    # expires_at если задан и в прошлом => истекло
    if sub.expires_at is not None:
        now = _utcnow()
        # expires_at в БД timezone-aware, сравнение корректное
        if sub.expires_at < now:
            raise SubscriptionExpiredError()

    return sub


# -------------------- public API --------------------

def get_active_plan_for_user(db: Session, user_or_id: int | User) -> Plan:
    """
    Возвращает активный план пользователя (по active subscription).

    Важно: принимает и user_id (int), и User объект.
    """
    user = _resolve_user(db, user_or_id)

    sub = _get_subscription_or_raise(user)

    # plan relationship может быть не загружен (lazy), но доступен через sub.plan
    plan: Plan | None = sub.plan
    if plan is None:
        # fallback: достать по plan_id
        plan = db.query(Plan).filter(Plan.id == sub.plan_id).one_or_none()

    if plan is None:
        # plan_code неизвестен, но для совместимости — отдаём заглушку
        raise PlanNotFoundError(plan_code="unknown")

    if not plan.is_active:
        raise PlanInactiveError(plan_code=plan.code)

    return plan


def enforce_max_servers(db: Session, user_or_id: int | User) -> None:
    user = _resolve_user(db, user_or_id)
    plan = get_active_plan_for_user(db, user)

    used = (
        db.query(func.count(Server.id))
        .filter(Server.owner_id == user.id, Server.deleted_at.is_(None))
        .scalar()
    )
    used_i = int(used or 0)
    limit_i = int(plan.max_servers or 0)

    if used_i >= limit_i:
        raise LimitExceededError(
            resource="servers",
            limit=limit_i,
            current=used_i,
        )


def enforce_max_devices(db: Session, user_or_id: int | User) -> None:
    user = _resolve_user(db, user_or_id)
    plan = get_active_plan_for_user(db, user)

    used = (
        db.query(func.count(Device.id))
        .filter(Device.user_id == user.id, Device.revoked_at.is_(None))
        .scalar()
    )
    used_i = int(used or 0)
    limit_i = int(plan.max_devices or 0)

    if used_i >= limit_i:
        raise LimitExceededError(
            resource="devices",
            limit=limit_i,
            current=used_i,
        )
