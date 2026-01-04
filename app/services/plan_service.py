from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.plan import Plan

logger = logging.getLogger(__name__)

try:
    from psycopg.errors import UniqueViolation  # type: ignore
except Exception:  # pragma: no cover
    UniqueViolation = None  # type: ignore


SYSTEM_PLAN_CODES: set[str] = {"free"}


@dataclass
class SystemPlanProtectedError(Exception):
    plan_code: str

    def message(self) -> str:
        return f"System plan is protected: {self.plan_code}"


@dataclass
class PlanCodeImmutableError(Exception):
    current: str
    requested: str

    def message(self) -> str:
        return "Plan code cannot be changed"


class PlanService:
    def __init__(self, db: Session):
        self.db = db

    def _handle_integrity_error(self, e: IntegrityError, *, unique_msg: str) -> None:
        orig = getattr(e, "orig", None)
        logger.exception("IntegrityError: %r", orig or e)

        if UniqueViolation is not None and isinstance(orig, UniqueViolation):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=unique_msg,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integrity constraint failed",
        )

    def _ensure_not_system_plan(self, plan: Plan) -> None:
        if plan.code in SYSTEM_PLAN_CODES:
            raise SystemPlanProtectedError(plan_code=plan.code)

    # -------- public (billing) --------
    def list_active(self) -> list[Plan]:
        return (
            self.db.query(Plan)
            .filter(Plan.is_active.is_(True))
            .order_by(Plan.price_cents.asc(), Plan.id.asc())
            .all()
        )

    # -------- admin --------
    def list_all_admin(self) -> list[Plan]:
        return self.db.query(Plan).order_by(Plan.id.asc()).all()

    def get_or_404(self, plan_id: int) -> Plan:
        plan = self.db.query(Plan).filter(Plan.id == plan_id).one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan

    def create(self, data: dict) -> Plan:
        plan = Plan(**data)
        self.db.add(plan)
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            self._handle_integrity_error(e, unique_msg="Plan code already exists")
        self.db.refresh(plan)
        return plan

    def update(self, plan: Plan, data: dict) -> Plan:
        # SaaS правило: code — стабильный идентификатор, не меняем
        if "code" in data and data["code"] != plan.code:
            raise PlanCodeImmutableError(current=plan.code, requested=str(data["code"]))

        for k, v in data.items():
            setattr(plan, k, v)

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            self._handle_integrity_error(e, unique_msg="Plan code already exists")

        self.db.refresh(plan)
        return plan

    def activate(self, plan: Plan) -> Plan:
        if plan.is_active:
            return plan
        plan.is_active = True
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def deactivate(self, plan: Plan) -> Plan:
        self._ensure_not_system_plan(plan)
        if not plan.is_active:
            return plan
        plan.is_active = False
        self.db.commit()
        self.db.refresh(plan)
        return plan
