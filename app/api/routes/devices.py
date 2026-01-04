from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.device import DeviceOut
from app.db.models.user import User
from app.db.session import get_db
from app.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceOut])
def list_devices(
    include_revoked: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Список устройств текущего пользователя.
    По умолчанию возвращаем только активные (revoked_at IS NULL).
    include_revoked=true -> вернуть и отозванные.
    """
    return DeviceService(db).list_owned(current_user.id, include_revoked=include_revoked)


@router.post("/{device_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Отозвать устройство по id (освобождает слот).
    """
    DeviceService(db).revoke_owned(device_id=device_id, owner_id=current_user.id)
    return None
