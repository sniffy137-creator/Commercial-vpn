from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class AdminBillingSummaryOut(BaseModel):
    status: str
    plan_code: str
    plan_name: str
    expires_at: datetime | None

    max_servers: int
    max_devices: int

    servers_used: int
    devices_used: int


class AdminBillingUserOut(BaseModel):
    id: int
    email: str
    role: str
    billing: AdminBillingSummaryOut
