from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.schemas.admin import AdminServerOut, AdminUserOut
from app.db.models.user import User
from app.db.session import get_db
from app.services.server_service import ServerService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/users", response_model=list[AdminUserOut])
def list_users(db: Session = Depends(get_db)):
    from app.db.models.user import User as UserModel
    return db.query(UserModel).order_by(UserModel.id).all()


@router.get("/servers", response_model=list[AdminServerOut])
def list_all_servers(db: Session = Depends(get_db)):
    """
    Админ видит ВСЕ серверы, включая soft-deleted
    """
    return ServerService(db).list_all_admin()


@router.post("/servers/{server_id}/delete", response_model=AdminServerOut)
def admin_soft_delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    """
    Админский soft delete (идемпотентно).
    """
    return ServerService(db).admin_soft_delete(server_id, actor_id=current_admin.id)


@router.post("/servers/{server_id}/restore", response_model=AdminServerOut)
def admin_restore_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user),
):
    """
    Админский restore (идемпотентно).
    """
    return ServerService(db).admin_restore(server_id, actor_id=current_admin.id)
