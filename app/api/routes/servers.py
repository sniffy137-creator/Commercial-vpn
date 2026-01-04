from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.server import ServerCreate, ServerOut, ServerUpdate
from app.db.models.user import User
from app.db.session import get_db
from app.services.server_service import ServerService

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("", response_model=list[ServerOut])
def list_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Пользователь видит ТОЛЬКО свои "живые" (не удалённые) серверы.
    """
    return ServerService(db).list_owned_live(current_user.id)


@router.post("", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
def create_server(
    payload: ServerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать сервер для текущего пользователя.
    """
    return ServerService(db).create_owned(
        payload=payload.model_dump(),
        owner_id=current_user.id,
        actor_id=current_user.id,
    )


@router.get("/{server_id}", response_model=ServerOut)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить конкретный сервер текущего пользователя (только не удалённый).
    """
    return ServerService(db).get_owned_live_or_404(server_id, current_user.id)


@router.patch("/{server_id}", response_model=ServerOut)
def update_server(
    server_id: int,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить сервер текущего пользователя (только не удалённый).
    """
    svc = ServerService(db)
    server = svc.get_owned_live_or_404(server_id, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    return svc.update_owned(server, data=data, actor_id=current_user.id)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete сервера текущего пользователя.
    """
    svc = ServerService(db)
    server = svc.get_owned_live_or_404(server_id, current_user.id)
    svc.soft_delete_owned(server, actor_id=current_user.id)
    return None
