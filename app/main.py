
import logging

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.session import get_db
from app.api.v1.categories import router as categories_router
from app.api.v1.brands import router as brands_router
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.product_variants import router as product_variants_router
from app.api.v1.cart import router as cart_router
from app.api.v1.orders import router as orders_router
from app.api.v1.addresses import router as addresses_router

configure_logging()
logger = logging.getLogger("app")
settings = get_settings()

app = FastAPI(
    title="Paw Pantry API",
    description="Backend API for the Paw Pantry dog-food store.",
    version="0.1.0",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app.include_router(
    categories_router,
    prefix="/api/v1",
)

app.include_router(
    brands_router,
    prefix="/api/v1",
)

app.include_router(
    auth_router, 
    prefix="/api/v1"
)

app.include_router(
    products_router,
    prefix="/api/v1"
)

app.include_router(
    product_variants_router,
    prefix="/api/v1",
)

app.include_router(
    cart_router,
    prefix="/api/v1",
)

app.include_router(
    orders_router,
    prefix="/api/v1",
)

app.include_router(
    addresses_router,
    prefix="/api/v1",
)

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "database": "unavailable",
            },
        ) from exc


@app.get("/health-simple", tags=["Health"])
def health_simple() -> dict[str, str]:
    return {"status": "ok"}
