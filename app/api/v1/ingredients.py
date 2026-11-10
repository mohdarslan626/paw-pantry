from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.models import Ingredient, User
from app.schemas.product_admin import IngredientCreate, IngredientResponse

router = APIRouter(prefix="/ingredients", tags=["Ingredients"])

@router.get("/", response_model=list[IngredientResponse])
def list_ingredients(db: Session = Depends(get_db)):
    return db.scalars(select(Ingredient).where(Ingredient.deleted_at.is_(None)).order_by(Ingredient.name)).all()

@router.post("/", response_model=IngredientResponse, status_code=status.HTTP_201_CREATED)
def create_ingredient(payload: IngredientCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    item = Ingredient(name=payload.name.strip(), description=payload.description)
    db.add(item)
    try:
        db.commit(); db.refresh(item)
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail="Ingredient already exists.") from exc
    return item
