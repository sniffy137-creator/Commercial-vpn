from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.schemas.admin_plan import AdminPlanCreate, AdminPlanOut, AdminPlanUpdate
from app.db.session import get_db
from app.services.plan_service import PlanService

router = APIRouter(
    prefix="/admin/plans",
    tags=["admin-plans"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[AdminPlanOut])
def list_plans(db: Session = Depends(get_db)):
    return PlanService(db).list_all_admin()


@router.post("", response_model=AdminPlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(payload: AdminPlanCreate, db: Session = Depends(get_db)):
    return PlanService(db).create(payload.model_dump())


@router.get("/{plan_id}", response_model=AdminPlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    return PlanService(db).get_or_404(plan_id)


@router.patch("/{plan_id}", response_model=AdminPlanOut)
def update_plan(plan_id: int, payload: AdminPlanUpdate, db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan = svc.get_or_404(plan_id)
    data = payload.model_dump(exclude_unset=True)
    return svc.update(plan, data)


@router.post("/{plan_id}/activate", response_model=AdminPlanOut)
def activate_plan(plan_id: int, db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan = svc.get_or_404(plan_id)
    return svc.activate(plan)


@router.post("/{plan_id}/deactivate", response_model=AdminPlanOut)
def deactivate_plan(plan_id: int, db: Session = Depends(get_db)):
    svc = PlanService(db)
    plan = svc.get_or_404(plan_id)
    return svc.deactivate(plan)
