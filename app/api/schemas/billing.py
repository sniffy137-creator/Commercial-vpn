from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BillingSummaryOut(BaseModel):
    status: str
    plan_code: str
    plan_name: str
    expires_at: datetime | None

    max_servers: int
    max_devices: int

    servers_used: int
    devices_used: int

    class Config:
        from_attributes = True


class RenewIn(BaseModel):
    plan_code: str
    days: int = 30


class PlanOut(BaseModel):
    code: str
    name: str
    price_cents: int
    currency: str
    max_servers: int
    max_devices: int
    is_active: bool

    class Config:
        from_attributes = True
