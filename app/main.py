from __future__ import annotations

from fastapi import FastAPI

from app.api.error_handlers import install_exception_handlers

# public routes
from app.api.routes.auth import router as auth_router
from app.api.routes.servers import router as servers_router
from app.api.routes.devices import router as devices_router
from app.api.routes.billing import router as billing_router  # ✅ ВАЖНО

# admin routes
from app.api.routes.admin import router as admin_router
from app.api.routes.admin_plans import router as admin_plans_router
from app.api.routes.admin_subscriptions import router as admin_subscriptions_router
from app.api.routes.admin_billing import router as admin_billing_router


def create_app() -> FastAPI:
    app = FastAPI()

    # error handlers first
    install_exception_handlers(app)

    # ===== public routers =====
    app.include_router(auth_router)
    app.include_router(servers_router)
    app.include_router(devices_router)
    app.include_router(billing_router)  # ✅ без этого были 404

    # ===== admin routers =====
    app.include_router(admin_router)
    app.include_router(admin_plans_router)
    app.include_router(admin_subscriptions_router)
    app.include_router(admin_billing_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
