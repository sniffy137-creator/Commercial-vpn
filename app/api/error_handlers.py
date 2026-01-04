from __future__ import annotations

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette import status

from app.services.limits import (
    LimitExceededError,
    NoActiveSubscriptionError,
)
from app.services.subscription_service import (
    PlanInactiveError,
    PlanNotFoundError,
    SubscriptionExpiredError,
)
from app.services.plan_service import (
    PlanCodeImmutableError,
    SystemPlanProtectedError,
)
from app.services.admin_subscription_service import (
    AdminUserNotFoundError,
    AdminPlanNotFoundError,
    AdminPlanInactiveError,
)


def install_exception_handlers(app: FastAPI) -> None:
    # -------- subscriptions / limits --------

    @app.exception_handler(NoActiveSubscriptionError)
    async def _no_active_subscription_handler(
        request: Request,
        exc: NoActiveSubscriptionError,
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": exc.message(),
                "code": "no_active_subscription",
            },
        )

    @app.exception_handler(LimitExceededError)
    async def _limit_exceeded_handler(
        request: Request,
        exc: LimitExceededError,
    ):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": exc.message(),
                "code": "plan_limit_exceeded",
                "meta": {
                    "resource": exc.resource,
                    "limit": exc.limit,
                    "current": exc.current,
                },
            },
        )

    @app.exception_handler(SubscriptionExpiredError)
    async def _subscription_expired_handler(
        request: Request,
        exc: SubscriptionExpiredError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": exc.message(),
                "code": "subscription_expired",
            },
        )

    # -------- plan resolution (user side) --------

    @app.exception_handler(PlanNotFoundError)
    async def _plan_not_found_handler(
        request: Request,
        exc: PlanNotFoundError,
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": exc.message(),
                "code": "plan_not_found",
                "meta": {
                    "plan_code": exc.plan_code,
                },
            },
        )

    @app.exception_handler(PlanInactiveError)
    async def _plan_inactive_handler(
        request: Request,
        exc: PlanInactiveError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": exc.message(),
                "code": "plan_inactive",
                "meta": {
                    "plan_code": exc.plan_code,
                },
            },
        )

    # -------- plan management (admin) --------

    @app.exception_handler(SystemPlanProtectedError)
    async def _system_plan_protected_handler(
        request: Request,
        exc: SystemPlanProtectedError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": exc.message(),
                "code": "system_plan_protected",
                "meta": {
                    "plan_code": exc.plan_code,
                },
            },
        )

    @app.exception_handler(PlanCodeImmutableError)
    async def _plan_code_immutable_handler(
        request: Request,
        exc: PlanCodeImmutableError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": exc.message(),
                "code": "plan_code_immutable",
                "meta": {
                    "current": exc.current,
                    "requested": exc.requested,
                },
            },
        )

    # -------- admin subscriptions --------

    @app.exception_handler(AdminUserNotFoundError)
    async def _admin_user_not_found_handler(
        request: Request,
        exc: AdminUserNotFoundError,
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": exc.message(),
                "code": "user_not_found",
                "meta": {
                    "user_id": exc.user_id,
                },
            },
        )

    @app.exception_handler(AdminPlanNotFoundError)
    async def _admin_plan_not_found_handler(
        request: Request,
        exc: AdminPlanNotFoundError,
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": exc.message(),
                "code": "plan_not_found",
                "meta": {
                    "plan_code": exc.plan_code,
                },
            },
        )

    @app.exception_handler(AdminPlanInactiveError)
    async def _admin_plan_inactive_handler(
        request: Request,
        exc: AdminPlanInactiveError,
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": exc.message(),
                "code": "plan_inactive",
                "meta": {
                    "plan_code": exc.plan_code,
                },
            },
        )
