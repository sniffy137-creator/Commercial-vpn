from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminSubscriptionOut(BaseModel):
    user_id: int
    status: str
    plan_code: str | None = None
    plan_name: str | None = None
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserWithSubscriptionOut(BaseModel):
    id: int
    email: str
    role: str
    subscription: AdminSubscriptionOut | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminGrantSubscriptionIn(BaseModel):
    plan_code: str = Field(min_length=1, max_length=32)
    # если None -> "без окончания" (lifetime / until canceled)
    expires_at: datetime | None = None


class AdminExtendSubscriptionIn(BaseModel):
    days: int = Field(ge=1, le=3650)  # до 10 лет, дальше уже странно


class AdminCancelSubscriptionIn(BaseModel):
    # если True -> сразу "canceled" и expires_at = now
    immediately: bool = True
