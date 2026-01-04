from pydantic import BaseModel, Field
from typing import Optional


class ServerBase(BaseModel):
    name: str = Field(..., max_length=120)
    host: str = Field(..., max_length=255)
    port: int = Field(default=51820, ge=1, le=65535)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)  # ISO2
    is_active: bool = True
    notes: Optional[str] = None


class ServerCreate(ServerBase):
    pass


class ServerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    host: Optional[str] = Field(default=None, max_length=255)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ServerOut(ServerBase):
    id: int
    owner_id: int

    class Config:
        from_attributes = True
