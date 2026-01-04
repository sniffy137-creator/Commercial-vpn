from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DeviceOut(BaseModel):
    id: int
    device_id: str
    device_name: str | None
    last_seen_at: datetime
    revoked_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
