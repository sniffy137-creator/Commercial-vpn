from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeviceOut(BaseModel):
    id: int
    device_id: str
    device_name: str | None
    last_seen_at: datetime
    revoked_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
