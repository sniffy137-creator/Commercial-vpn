from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.server import Server
from app.services.limits import enforce_max_servers

logger = logging.getLogger(__name__)

# psycopg v3 error classes
try:
    from psycopg.errors import UniqueViolation  # type: ignore
except Exception:  # pragma: no cover
    UniqueViolation = None  # type: ignore


class ServerService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- helpers ----------
    def _handle_integrity_error(self, e: IntegrityError, *, unique_msg: str) -> None:
        """
        Мапим database integrity ошибки в корректные HTTP-коды.
        - UniqueViolation -> 409
        - остальное -> 400
        """
        orig = getattr(e, "orig", None)
        logger.exception("IntegrityError: %r", orig or e)

        if UniqueViolation is not None and isinstance(orig, UniqueViolation):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=unique_msg,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integrity constraint failed",
        )

    def _enforce_create_limits(self, owner_id: int) -> None:
        """
        Enforcement лимитов для создания сервера (Variant C).
        Вся логика подписки/плана/админа — внутри enforce_max_servers().
        """
        enforce_max_servers(self.db, owner_id)

    # ---------- USER ----------
    def list_owned_live(self, owner_id: int) -> list[Server]:
        """
        Пользователь видит только свои активные (не удалённые) серверы.
        """
        return (
            self.db.query(Server)
            .filter(Server.owner_id == owner_id, Server.deleted_at.is_(None))
            .order_by(Server.id.desc())
            .all()
        )

    def get_owned_live_or_404(self, server_id: int, owner_id: int) -> Server:
        """
        Получить конкретный сервер пользователя (только активный).
        """
        server = (
            self.db.query(Server)
            .filter(
                Server.id == server_id,
                Server.owner_id == owner_id,
                Server.deleted_at.is_(None),
            )
            .one_or_none()
        )
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        return server

    def create_owned(self, payload: dict, owner_id: int, actor_id: int) -> Server:
        """
        Создать сервер пользователя.
        """
        # 🔒 enforce plan limits
        self._enforce_create_limits(owner_id)

        server = Server(
            **payload,
            owner_id=owner_id,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.db.add(server)

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            self._handle_integrity_error(
                e,
                unique_msg="Server endpoint already exists (host+port)",
            )

        self.db.refresh(server)
        return server

    def update_owned(self, server: Server, data: dict, actor_id: int) -> Server:
        """
        Обновить сервер пользователя.
        """
        for k, v in data.items():
            setattr(server, k, v)
        server.updated_by = actor_id

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            self._handle_integrity_error(
                e,
                unique_msg="Server endpoint already exists (host+port)",
            )

        self.db.refresh(server)
        return server

    def soft_delete_owned(self, server: Server, actor_id: int) -> None:
        """
        Soft delete сервера пользователя.
        """
        server.deleted_at = func.now()
        server.deleted_by = actor_id
        server.updated_by = actor_id
        self.db.commit()

    # ---------- ADMIN ----------
    def list_all_admin(self) -> list[Server]:
        """
        Админ видит все серверы, включая удалённые.
        """
        return self.db.query(Server).order_by(Server.id.desc()).all()

    def get_any_or_404(self, server_id: int) -> Server:
        """
        Админ: получить любой сервер (включая удалённый).
        """
        server = self.db.query(Server).filter(Server.id == server_id).one_or_none()
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        return server

    def admin_soft_delete(self, server_id: int, actor_id: int) -> Server:
        """
        Админ: soft delete любого сервера.
        """
        server = self.get_any_or_404(server_id)
        if server.deleted_at is not None:
            return server

        server.deleted_at = func.now()
        server.deleted_by = actor_id
        server.updated_by = actor_id

        self.db.commit()
        self.db.refresh(server)
        return server

    def admin_restore(self, server_id: int, actor_id: int) -> Server:
        """
        Админ: восстановить сервер (undo soft delete).
        Важно: может упасть по partial unique index (host+port для active).
        """
        server = self.get_any_or_404(server_id)
        if server.deleted_at is None:
            return server

        server.deleted_at = None
        server.restored_by = actor_id
        server.updated_by = actor_id

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            self._handle_integrity_error(
                e,
                unique_msg="Cannot restore: active server with same host+port already exists",
            )

        self.db.refresh(server)
        return server
