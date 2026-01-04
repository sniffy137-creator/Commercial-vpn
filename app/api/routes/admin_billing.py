from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_admin
from app.api.schemas.admin_billing import AdminBillingUserOut
from app.db.models.subscription import Subscription
from app.db.models.user import User
from app.db.session import get_db
from app.services.billing_service import BillingService

router = APIRouter(
    prefix="/admin/billing",
    tags=["admin-billing"],
    dependencies=[Depends(require_admin)],
)


@router.get("/users", response_model=list[AdminBillingUserOut])
def list_users_billing(db: Session = Depends(get_db)):
    """
    Админ-таблица для UI: список пользователей + billing summary.
    """
    users: list[User] = (
        db.query(User)
        .options(
            selectinload(User.subscription).selectinload(Subscription.plan)
        )
        .order_by(User.id.asc())
        .all()
    )

    billing = BillingService(db)

    out: list[AdminBillingUserOut] = []
    for u in users:
        out.append(
            AdminBillingUserOut(
                id=u.id,
                email=u.email,
                role=u.role,
                billing=billing.summary(u),
            )
        )
    return out
