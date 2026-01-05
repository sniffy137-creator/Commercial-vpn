from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AdminPlanBase(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)

    price_cents: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)

    max_servers: int = Field(ge=0)  # 0 = unlimited
    max_devices: int = Field(ge=0)  # 0 = unlimited

    is_active: bool = True


class AdminPlanCreate(AdminPlanBase):
    pass


class AdminPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)

    price_cents: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    max_servers: int | None = Field(default=None, ge=0)
    max_devices: int | None = Field(default=None, ge=0)

    is_active: bool | None = None


class AdminPlanOut(AdminPlanBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
