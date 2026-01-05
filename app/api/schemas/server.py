from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ServerBase(BaseModel):
    name: str = Field(..., max_length=120)
    host: str = Field(..., max_length=255)
    port: int = Field(default=51820, ge=1, le=65535)
    country: str | None = Field(default=None, min_length=2, max_length=2)  # ISO2
    is_active: bool = True
    notes: str | None = None


class ServerCreate(ServerBase):
    pass


class ServerUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    country: str | None = None
    notes: str | None = None


class ServerOut(ServerBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)
