from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.models import Ingredient, NutritionalAnalysis, Product, ProductIngredient, User
from app.schemas.product import ProductIngredientResponse, NutritionalAnalysisResponse
from app.schemas.product_admin import ProductIngredientCreate, ProductIngredientUpdate, NutritionCreate, NutritionUpdate

router = APIRouter(prefix="/products/{product_id}", tags=["Product Composition"])

def _product(db: Session, product_id: UUID):
    product = db.get(Product, product_id)
    if product is None or product.deleted_at is not None: raise HTTPException(status_code=404, detail="Product not found.")
    return product

@router.get("/ingredients", response_model=list[ProductIngredientResponse])
def list_product_ingredients(product_id: UUID, db: Session = Depends(get_db)):
    _product(db, product_id)
    rows = db.scalars(select(ProductIngredient).where(ProductIngredient.product_id == product_id, ProductIngredient.deleted_at.is_(None)).options(selectinload(ProductIngredient.ingredient)).order_by(ProductIngredient.display_order)).all()
    return rows

@router.post("/ingredients", response_model=ProductIngredientResponse, status_code=status.HTTP_201_CREATED)
def add_product_ingredient(product_id: UUID, payload: ProductIngredientCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    _product(db, product_id)
    if payload.ingredient_id is not None:
        ingredient = db.get(Ingredient, payload.ingredient_id)
        if ingredient is None or ingredient.deleted_at is not None: raise HTTPException(status_code=404, detail="Ingredient not found.")
    else:
        ingredient = db.scalar(select(Ingredient).where(Ingredient.name == payload.name, Ingredient.deleted_at.is_(None)))
        if ingredient is None:
            ingredient = Ingredient(name=payload.name.strip(), description=payload.description); db.add(ingredient); db.flush()
    row = ProductIngredient(product_id=product_id, ingredient_id=ingredient.id, percentage=payload.percentage, display_order=payload.display_order)
    db.add(row)
    try: db.commit(); db.refresh(row)
    except IntegrityError as exc: db.rollback(); raise HTTPException(status_code=409, detail="Ingredient is already linked to this product or conflicts with existing data.") from exc
    return db.scalar(select(ProductIngredient).where(ProductIngredient.id == row.id).options(selectinload(ProductIngredient.ingredient)))

@router.patch("/ingredients/{link_id}", response_model=ProductIngredientResponse)
def update_product_ingredient(product_id: UUID, link_id: UUID, payload: ProductIngredientUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    row = db.scalar(select(ProductIngredient).where(ProductIngredient.id == link_id, ProductIngredient.product_id == product_id, ProductIngredient.deleted_at.is_(None)).options(selectinload(ProductIngredient.ingredient)))
    if row is None: raise HTTPException(status_code=404, detail="Product ingredient not found.")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    db.commit(); return row

@router.delete("/ingredients/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_product_ingredient(product_id: UUID, link_id: UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    row = db.scalar(select(ProductIngredient).where(ProductIngredient.id == link_id, ProductIngredient.product_id == product_id, ProductIngredient.deleted_at.is_(None)))
    if row is None: raise HTTPException(status_code=404, detail="Product ingredient not found.")
    from datetime import datetime, timezone
    row.deleted_at = datetime.now(timezone.utc); db.commit()

@router.get("/nutrition", response_model=list[NutritionalAnalysisResponse])
def list_product_nutrition(product_id: UUID, db: Session = Depends(get_db)):
    _product(db, product_id)
    return db.scalars(select(NutritionalAnalysis).where(NutritionalAnalysis.product_id == product_id, NutritionalAnalysis.deleted_at.is_(None)).order_by(NutritionalAnalysis.nutrient_code)).all()

@router.post("/nutrition", response_model=NutritionalAnalysisResponse, status_code=status.HTTP_201_CREATED)
def add_product_nutrition(product_id: UUID, payload: NutritionCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    _product(db, product_id)
    row = NutritionalAnalysis(product_id=product_id, **payload.model_dump()); db.add(row)
    try: db.commit(); db.refresh(row)
    except IntegrityError as exc: db.rollback(); raise HTTPException(status_code=409, detail="This nutrient and basis already exist for the product.") from exc
    return row

@router.patch("/nutrition/{nutrition_id}", response_model=NutritionalAnalysisResponse)
def update_product_nutrition(product_id: UUID, nutrition_id: UUID, payload: NutritionUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    row = db.scalar(select(NutritionalAnalysis).where(NutritionalAnalysis.id == nutrition_id, NutritionalAnalysis.product_id == product_id, NutritionalAnalysis.deleted_at.is_(None)))
    if row is None: raise HTTPException(status_code=404, detail="Nutrition row not found.")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    db.commit(); return row

@router.delete("/nutrition/{nutrition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_nutrition(product_id: UUID, nutrition_id: UUID, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    row = db.scalar(select(NutritionalAnalysis).where(NutritionalAnalysis.id == nutrition_id, NutritionalAnalysis.product_id == product_id, NutritionalAnalysis.deleted_at.is_(None)))
    if row is None: raise HTTPException(status_code=404, detail="Nutrition row not found.")
    from datetime import datetime, timezone
    row.deleted_at = datetime.now(timezone.utc); db.commit()
