
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import (
    Brand,
    Category,
    Inventory,
    InventoryLocation,
    Product,
    ProductStatus,
    ProductVariant,
)


BRAND = {
    "name": "Paw Pantry",
    "slug": "paw-pantry",
    "description": "Thoughtfully selected food and nutrition for dogs.",
}

CATEGORIES = [
    {
        "name": "Dry Food",
        "slug": "dry-food",
        "description": "Complete dry food for dogs.",
    },
    {
        "name": "Wet Food",
        "slug": "wet-food",
        "description": "Moist and flavorful meals for dogs.",
    },
    {
        "name": "Treats",
        "slug": "dog-treats",
        "description": "Treats for training and everyday rewards.",
    },
    {
        "name": "Supplements",
        "slug": "dog-supplements",
        "description": "Supplementary nutrition for dogs.",
    },
]

PRODUCTS = [
    {
        "name": "Chicken & Brown Rice",
        "slug": "chicken-brown-rice",
        "category": "dry-food",
        "short_description": "A balanced everyday meal for adult dogs.",
        "description": "Chicken and brown rice adult dog food.",
        "variants": [
            {"sku": "PP-CHICKEN-1KG", "name": "1 kg pack",
             "weight": 1000, "price": "1299.00", "stock": 25},
            {"sku": "PP-CHICKEN-3KG", "name": "3 kg pack",
             "weight": 3000, "price": "3299.00", "stock": 12},
        ],
    },
    {
        "name": "Salmon & Sweet Potato",
        "slug": "salmon-sweet-potato",
        "category": "dry-food",
        "short_description": "Salmon and sweet potato recipe for dogs.",
        "description": "A salmon-based dry food recipe.",
        "variants": [
            {"sku": "PP-SALMON-1KG", "name": "1 kg pack",
             "weight": 1000, "price": "1499.00", "stock": 20},
        ],
    },
    {
        "name": "Puppy Growth Formula",
        "slug": "puppy-growth-formula",
        "category": "dry-food",
        "short_description": "Daily nutrition for growing puppies.",
        "description": "A dry food recipe formulated for puppies.",
        "variants": [
            {"sku": "PP-PUPPY-1KG", "name": "1 kg pack",
             "weight": 1000, "price": "1199.00", "stock": 18},
        ],
    },
    {
        "name": "Chicken Gravy Meal",
        "slug": "chicken-gravy-meal",
        "category": "wet-food",
        "short_description": "A convenient wet meal for dogs.",
        "description": "Chicken wet food served in a savory gravy.",
        "variants": [
            {"sku": "PP-GRAVY-400G", "name": "400 g pack",
             "weight": 400, "price": "199.00", "stock": 40},
        ],
    },
    {
        "name": "Joint Care Chews",
        "slug": "joint-care-chews",
        "category": "dog-supplements",
        "short_description": "Chewable nutritional supplement for dogs.",
        "description": "A supplement product for your dog.",
        "variants": [
            {"sku": "PP-JOINT-60", "name": "60 chews",
             "weight": None, "price": "899.00", "stock": 15},
        ],
    },
]

LOCATION = {
    "code": "MAIN-WH",
    "name": "Main Warehouse",
}


def seed() -> None:
    db = SessionLocal()

    try:
        # Create or reuse the brand.
        brand = db.scalar(
            select(Brand).where(
                Brand.slug == BRAND["slug"],
                Brand.deleted_at.is_(None),
            )
        )

        if brand is None:
            brand = Brand(**BRAND)
            db.add(brand)
            db.flush()

        # Create or reuse categories.
        categories_by_slug = {}

        for data in CATEGORIES:
            category = db.scalar(
                select(Category).where(
                    Category.slug == data["slug"],
                    Category.deleted_at.is_(None),
                )
            )

            if category is None:
                category = Category(**data)
                db.add(category)
                db.flush()

            categories_by_slug[data["slug"]] = category

        # Create or reuse the inventory location.
        location = db.scalar(
            select(InventoryLocation).where(
                InventoryLocation.code == LOCATION["code"]
            )
        )

        if location is None:
            location = InventoryLocation(**LOCATION)
            db.add(location)
            db.flush()

        # Create products, variants, and inventory.
        for data in PRODUCTS:
            product = db.scalar(
                select(Product).where(
                    Product.slug == data["slug"],
                    Product.deleted_at.is_(None),
                )
            )

            if product is None:
                product = Product(
                    brand_id=brand.id,
                    category_id=categories_by_slug[data["category"]].id,
                    name=data["name"],
                    slug=data["slug"],
                    short_description=data["short_description"],
                    description=data["description"],
                    status=ProductStatus.ACTIVE,
                    published_at=datetime.now(timezone.utc),
                )
                db.add(product)
                db.flush()

            # Reuse variants by SKU.
            for variant_data in data["variants"]:
                variant = db.scalar(
                    select(ProductVariant).where(
                        ProductVariant.sku == variant_data["sku"],
                        ProductVariant.deleted_at.is_(None),
                    )
                )

                if variant is None:
                    variant = ProductVariant(
                        product_id=product.id,
                        sku=variant_data["sku"],
                        variant_name=variant_data["name"],
                        weight_grams=variant_data["weight"],
                        price=Decimal(variant_data["price"]),
                        currency="INR",
                        is_active=True,
                    )
                    db.add(variant)
                    db.flush()

                # One inventory record per variant and location.
                inventory = db.scalar(
                    select(Inventory).where(
                        Inventory.variant_id == variant.id,
                        Inventory.location_id == location.id,
                    )
                )

                if inventory is None:
                    db.add(
                        Inventory(
                            variant_id=variant.id,
                            location_id=location.id,
                            on_hand=variant_data["stock"],
                            reserved=0,
                        )
                    )

        db.commit()
        print("Seed data created successfully.")

        print(
            "Products:",
            db.scalar(
                select(__import__(
                    "sqlalchemy"
                ).func.count()).select_from(Product).where(
                    Product.deleted_at.is_(None)
                )
            ),
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
