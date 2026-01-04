from datetime import datetime

from pydantic import BaseModel, EmailStr


class AdminUserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminServerOut(BaseModel):
    id: int
    name: str
    host: str
    port: int
    country: str | None = None
    is_active: bool
    notes: str | None = None
    owner_id: int

    deleted_at: datetime | None = None

    # audit trail (admin видит)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: int | None = None
    updated_by: int | None = None
    deleted_by: int | None = None
    restored_by: int | None = None

    model_config = {"from_attributes": True}
