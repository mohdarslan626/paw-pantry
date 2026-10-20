
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.categories import router as categories_router
from app.api.v1.brands import router as brands_router
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.product_variants import router as product_variants_router
from app.api.v1.cart import router as cart_router
from app.api.v1.orders import router as orders_router

app = FastAPI(
    title="Paw Pantry API",
    description="Backend API for the Paw Pantry dog-food store.",
    version="0.1.0",
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
