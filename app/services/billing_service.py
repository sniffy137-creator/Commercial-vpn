from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.device import Device
from app.db.models.server import Server
from app.db.models.subscription import Subscription
from app.db.models.user import User


class BillingService:
    """
    One-call summary for UI:
    - plan/limits
    - usage counters
    - subscription status/expiry
    """

    def __init__(self, db: Session):
        self.db = db

    def summary(self, user: User) -> dict:
        # --- usage counters ---
        servers_used = (
            self.db.query(func.count(Server.id))
            .filter(
                Server.owner_id == user.id,
                Server.deleted_at.is_(None),
            )
            .scalar()
        )

        devices_used = (
            self.db.query(func.count(Device.id))
            .filter(
                Device.user_id == user.id,
                Device.revoked_at.is_(None),
            )
            .scalar()
        )

        # --- defaults (FREE / fallback) ---
        status = "none"
        plan_code = "free"
        plan_name = "Free"
        expires_at = None
        max_servers = 1
        max_devices = 1

        sub: Subscription | None = getattr(user, "subscription", None)
        if sub:
            status = sub.status
            expires_at = sub.expires_at

            # 🔹 UI-логика: active + expires_at в прошлом → expired
            if status == "active" and expires_at is not None:
                now = datetime.now(timezone.utc)
                if expires_at <= now:
                    status = "expired"

            # показываем план даже если expired / canceled
            if sub.plan is not None:
                plan_code = sub.plan.code
                plan_name = sub.plan.name
                max_servers = sub.plan.max_servers
                max_devices = sub.plan.max_devices

        return {
            "status": status,
            "plan_code": plan_code,
            "plan_name": plan_name,
            "expires_at": expires_at,
            "max_servers": max_servers,
            "max_devices": max_devices,
            "servers_used": int(servers_used or 0),
            "devices_used": int(devices_used or 0),
        }
