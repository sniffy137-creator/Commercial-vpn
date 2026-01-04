from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.device import Device
from app.db.models.user import User
from app.services.limits import LimitExceededError, NoActiveSubscriptionError, get_active_plan_for_user


@dataclass
class DeviceIdRequiredError(Exception):
    def message(self) -> str:
        return "X-Device-Id header is required"


class DeviceService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- LOGIN ENFORCEMENT ----------
    def register_or_touch_login_device(
        self,
        *,
        user: User,
        device_id: str | None,
        device_name: str | None = None,
    ) -> None:
        """
        Регистрирует устройство при логине или обновляет last_seen.
        Enforce max_devices для НЕ-админа.
        """
        if user.role == "admin":
            return

        if not device_id or not device_id.strip():
            raise DeviceIdRequiredError()

        device_id = device_id.strip()
        now = datetime.now(timezone.utc)

        existing = (
            self.db.query(Device)
            .filter(
                Device.user_id == user.id,
                Device.device_id == device_id,
                Device.revoked_at.is_(None),
            )
            .one_or_none()
        )

        if existing:
            existing.last_seen_at = now
            if device_name is not None and device_name.strip():
                existing.device_name = device_name.strip()
            self.db.commit()
            return

        plan = get_active_plan_for_user(self.db, user.id)

        if plan is None:
            raise NoActiveSubscriptionError()

        limit = plan.max_devices

        # limit <= 0 -> безлимит
        if limit > 0:
            current = (
                self.db.query(func.count(Device.id))
                .filter(
                    Device.user_id == user.id,
                    Device.revoked_at.is_(None),
                )
                .scalar()
            )
            if current >= limit:
                raise LimitExceededError(resource="devices", limit=limit, current=current)

        new_dev = Device(
            user_id=user.id,
            device_id=device_id,
            device_name=device_name.strip() if device_name and device_name.strip() else None,
            last_seen_at=now,
        )
        self.db.add(new_dev)
        self.db.commit()

    # ---------- USER UX ----------
    def list_owned(self, owner_id: int, *, include_revoked: bool = False) -> list[Device]:
        q = self.db.query(Device).filter(Device.user_id == owner_id)
        if not include_revoked:
            q = q.filter(Device.revoked_at.is_(None))
        return q.order_by(Device.last_seen_at.desc(), Device.id.desc()).all()

    def revoke_owned(self, *, device_id: int, owner_id: int) -> None:
        dev = (
            self.db.query(Device)
            .filter(Device.id == device_id, Device.user_id == owner_id)
            .one_or_none()
        )
        if not dev:
            # 404 в стиле остальных сервисов
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Device not found")

        if dev.revoked_at is None:
            dev.revoked_at = func.now()
            self.db.commit()
