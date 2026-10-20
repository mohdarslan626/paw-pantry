from __future__ import annotations
import enum, uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey,
    Index, Integer, Numeric, String, Text, UniqueConstraint, func, text)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", use_alter=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", use_alter=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", use_alter=True), nullable=True)

class UserStatus(str, enum.Enum):
    ACTIVE="active"; INVITED="invited"; SUSPENDED="suspended"; CLOSED="closed"
class ProductStatus(str, enum.Enum):
    DRAFT="draft"; ACTIVE="active"; ARCHIVED="archived"; OUT_OF_STOCK="out_of_stock"
class OrderStatus(str, enum.Enum):
    PENDING="pending"; CONFIRMED="confirmed"; PROCESSING="processing"; SHIPPED="shipped"; DELIVERED="delivered"; CANCELLED="cancelled"; REFUNDED="refunded"
class PaymentStatus(str, enum.Enum):
    PENDING="pending"; AUTHORIZED="authorized"; CAPTURED="captured"; FAILED="failed"; CANCELLED="cancelled"; REFUNDED="refunded"; PARTIALLY_REFUNDED="partially_refunded"
class SubscriptionStatus(str, enum.Enum):
    ACTIVE="active"; PAUSED="paused"; PAST_DUE="past_due"; CANCELLED="cancelled"; EXPIRED="expired"
class DiscountType(str, enum.Enum):
    PERCENTAGE="percentage"; FIXED_AMOUNT="fixed_amount"
class ContentStatus(str, enum.Enum):
    DRAFT="draft"; PUBLISHED="published"; ARCHIVED="archived"
class MediaStatus(str, enum.Enum):
    PENDING="pending"; READY="ready"; FAILED="failed"; RETIRED="retired"

class User(Base, AuditMixin):
    __tablename__="users"
    __table_args__=(Index("uq_users_email_active","email_normalized",unique=True,postgresql_where=text("deleted_at IS NULL")),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    email: Mapped[str]=mapped_column(String(320),nullable=False)
    email_normalized: Mapped[str]=mapped_column(String(320),nullable=False)
    password_hash: Mapped[Optional[str]]=mapped_column(String(255))
    display_name: Mapped[Optional[str]]=mapped_column(String(160))
    status: Mapped[UserStatus]=mapped_column(Enum(UserStatus,name="user_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),default=UserStatus.ACTIVE,nullable=False)
    last_login_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    roles: Mapped[List["Role"]] = relationship(
    "Role",
    secondary="user_roles",
    primaryjoin="User.id == UserRole.user_id",
    secondaryjoin="Role.id == UserRole.role_id",
    back_populates="users",
    overlaps="user,role",)
    addresses: Mapped[List["UserAddress"]]=relationship(back_populates="user",foreign_keys="UserAddress.user_id")
    dogs: Mapped[List["DogProfile"]]=relationship(back_populates="user",foreign_keys="DogProfile.user_id")
    carts: Mapped[List["Cart"]]=relationship(back_populates="user",foreign_keys="Cart.user_id")
    orders: Mapped[List["Order"]]=relationship(back_populates="user",foreign_keys="Order.user_id")
    subscriptions: Mapped[List["Subscription"]]=relationship(back_populates="user",foreign_keys="Subscription.user_id")
    reviews: Mapped[List["Review"]]=relationship(back_populates="user",foreign_keys="Review.user_id")

class Role(Base, AuditMixin):
    __tablename__="roles"
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    name: Mapped[str]=mapped_column(String(80),unique=True,nullable=False)
    description: Mapped[Optional[str]]=mapped_column(String(255))
    users: Mapped[List["User"]] = relationship(
    "User",
    secondary="user_roles",
    primaryjoin="Role.id == UserRole.role_id",
    secondaryjoin="User.id == UserRole.user_id",
    back_populates="roles",
    overlaps="user,role",)
class UserRole(Base, AuditMixin):
    __tablename__="user_roles"
    __table_args__=(UniqueConstraint("user_id","role_id",name="uq_user_role"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id"),nullable=False)
    role_id: Mapped[int]=mapped_column(ForeignKey("roles.id"),nullable=False)
    user: Mapped[User]=relationship(foreign_keys=[user_id])
    role: Mapped[Role]=relationship(foreign_keys=[role_id])
class UserAddress(Base, AuditMixin):
    __tablename__="user_addresses"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id"),nullable=False)
    address_type: Mapped[str]=mapped_column(String(20),default="shipping")
    recipient_name: Mapped[str]=mapped_column(String(160),nullable=False)
    phone: Mapped[Optional[str]]=mapped_column(String(32))
    line1: Mapped[str]=mapped_column(String(255),nullable=False)
    line2: Mapped[Optional[str]]=mapped_column(String(255))
    city: Mapped[str]=mapped_column(String(120),nullable=False)
    state_region: Mapped[str]=mapped_column(String(120),nullable=False)
    postal_code: Mapped[str]=mapped_column(String(24),nullable=False)
    country_code: Mapped[str]=mapped_column(String(2),default="IN",nullable=False)
    is_default: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
    user: Mapped[User]=relationship(back_populates="addresses",foreign_keys=[user_id])

class Brand(Base, AuditMixin):
    __tablename__="brands"
    __table_args__=(Index("uq_brand_slug_active","slug",unique=True,postgresql_where=text("deleted_at IS NULL")),)
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    name: Mapped[str]=mapped_column(String(160),nullable=False)
    slug: Mapped[str]=mapped_column(String(180),nullable=False)
    description: Mapped[Optional[str]]=mapped_column(Text)
    products: Mapped[List["Product"]]=relationship(back_populates="brand")
class Category(Base, AuditMixin):
    __tablename__="categories"
    __table_args__=(Index("uq_category_slug_active","slug",unique=True,postgresql_where=text("deleted_at IS NULL")),)
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    parent_id: Mapped[Optional[int]]=mapped_column(ForeignKey("categories.id"))
    name: Mapped[str]=mapped_column(String(160),nullable=False)
    slug: Mapped[str]=mapped_column(String(180),nullable=False)
    description: Mapped[Optional[str]]=mapped_column(Text)
    parent: Mapped[Optional["Category"]]=relationship(remote_side="Category.id",back_populates="children",foreign_keys=[parent_id])
    children: Mapped[List["Category"]]=relationship(back_populates="parent",foreign_keys=[parent_id])
    products: Mapped[List["Product"]]=relationship(back_populates="category")
class Product(Base, AuditMixin):
    __tablename__="products"
    __table_args__=(Index("uq_product_slug_active","slug",unique=True,postgresql_where=text("deleted_at IS NULL")),Index("ix_products_category_status","category_id","status"))
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    brand_id: Mapped[Optional[int]]=mapped_column(ForeignKey("brands.id"))
    category_id: Mapped[int]=mapped_column(ForeignKey("categories.id"),nullable=False)
    name: Mapped[str]=mapped_column(String(240),nullable=False)
    slug: Mapped[str]=mapped_column(String(260),nullable=False)
    short_description: Mapped[Optional[str]]=mapped_column(String(500))
    description: Mapped[Optional[str]]=mapped_column(Text)
    status: Mapped[ProductStatus]=mapped_column(Enum(ProductStatus,name="product_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),default=ProductStatus.DRAFT,nullable=False)
    published_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    brand: Mapped[Optional[Brand]]=relationship(back_populates="products")
    category: Mapped[Category]=relationship(back_populates="products")
    variants: Mapped[List["ProductVariant"]]=relationship(back_populates="product",foreign_keys="ProductVariant.product_id")
    images: Mapped[List["ProductImage"]]=relationship(back_populates="product",order_by="ProductImage.position")
    ingredients: Mapped[List["ProductIngredient"]]=relationship(back_populates="product")
    nutrition: Mapped[List["NutritionalAnalysis"]]=relationship(back_populates="product")
    reviews: Mapped[List["Review"]]=relationship(back_populates="product")
class ProductVariant(Base, AuditMixin):
    __tablename__="product_variants"
    __table_args__ = (
    Index(
        "uq_variant_sku_active",
        "sku",
        unique=True,
        postgresql_where=text("deleted_at IS NULL"),
    ),
    CheckConstraint("price >= 0", name="price_nonnegative"),
    CheckConstraint(
        "weight_grams IS NULL OR weight_grams > 0",
        name="weight_positive",
    ),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id"),nullable=False)
    sku: Mapped[str]=mapped_column(String(100),nullable=False)
    variant_name: Mapped[str]=mapped_column(String(160),nullable=False)
    weight_grams: Mapped[Optional[int]]=mapped_column(Integer)
    price: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    currency: Mapped[str]=mapped_column(String(3),default="INR",nullable=False)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)
    product: Mapped[Product]=relationship(back_populates="variants",foreign_keys=[product_id])
    inventory: Mapped[List["Inventory"]]=relationship(back_populates="variant")
    movements: Mapped[List["InventoryMovement"]]=relationship(back_populates="variant")
    cart_items: Mapped[List["CartItem"]]=relationship(back_populates="variant")
    order_items: Mapped[List["OrderItem"]]=relationship(back_populates="variant")
    subscription_items: Mapped[List["SubscriptionItem"]]=relationship(back_populates="variant")
class Ingredient(Base, AuditMixin):
    __tablename__="ingredients"
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    name: Mapped[str]=mapped_column(String(160),unique=True,nullable=False)
    description: Mapped[Optional[str]]=mapped_column(Text)
    product_links: Mapped[List["ProductIngredient"]]=relationship(back_populates="ingredient")
class ProductIngredient(Base, AuditMixin):
    __tablename__="product_ingredients"
    __table_args__ = (
    UniqueConstraint("product_id", "ingredient_id"),
    CheckConstraint(
        "percentage IS NULL OR percentage BETWEEN 0 AND 100",
        name="percentage_range",
    ),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id"),nullable=False)
    ingredient_id: Mapped[int]=mapped_column(ForeignKey("ingredients.id"),nullable=False)
    display_order: Mapped[int]=mapped_column(Integer,default=0,nullable=False)
    percentage: Mapped[Optional[Decimal]]=mapped_column(Numeric(5,2))
    product: Mapped[Product]=relationship(back_populates="ingredients")
    ingredient: Mapped[Ingredient]=relationship(back_populates="product_links")
class NutritionalAnalysis(Base, AuditMixin):
    __tablename__="nutritional_analyses"
    __table_args__=(UniqueConstraint("product_id","nutrient_code","basis"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id"),nullable=False)
    nutrient_code: Mapped[str]=mapped_column(String(80),nullable=False)
    value: Mapped[Decimal]=mapped_column(Numeric(12,5),nullable=False)
    unit: Mapped[str]=mapped_column(String(32),nullable=False)
    basis: Mapped[str]=mapped_column(String(32),default="as_fed",nullable=False)
    product: Mapped[Product]=relationship(back_populates="nutrition")
class MediaAsset(Base, AuditMixin):
    __tablename__="media_assets"
    __table_args__ = (
    CheckConstraint("size_bytes >= 0", name="size_nonnegative"),
    Index("ix_media_status_created", "status", "created_at"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    uploaded_by: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("users.id"))
    object_key: Mapped[str]=mapped_column(String(512),unique=True,nullable=False)
    original_filename: Mapped[Optional[str]]=mapped_column(String(255))
    mime_type: Mapped[str]=mapped_column(String(120),nullable=False)
    size_bytes: Mapped[int]=mapped_column(BigInteger,nullable=False)
    checksum_sha256: Mapped[Optional[str]]=mapped_column(String(64))
    status: Mapped[MediaStatus]=mapped_column(Enum(MediaStatus,name="media_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),default=MediaStatus.PENDING,nullable=False)
    alt_text: Mapped[Optional[str]]=mapped_column(String(255))
    product_links: Mapped[List["ProductImage"]]=relationship(back_populates="media_asset")
class ProductImage(Base, AuditMixin):
    __tablename__="product_images"
    __table_args__=(UniqueConstraint("product_id","media_asset_id"),Index("ix_product_images_position","product_id","position"))
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id"),nullable=False)
    media_asset_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("media_assets.id"),nullable=False)
    alt_text: Mapped[Optional[str]]=mapped_column(String(255))
    position: Mapped[int]=mapped_column(Integer,default=0,nullable=False)
    is_primary: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
    product: Mapped[Product]=relationship(back_populates="images")
    media_asset: Mapped[MediaAsset]=relationship(back_populates="product_links")
class InventoryLocation(Base, AuditMixin):
    __tablename__="inventory_locations"
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    code: Mapped[str]=mapped_column(String(60),unique=True,nullable=False)
    name: Mapped[str]=mapped_column(String(160),nullable=False)
    inventory: Mapped[List["Inventory"]]=relationship(back_populates="location")
class Inventory(Base, AuditMixin):
    __tablename__="inventory"
    __table_args__ = (
    UniqueConstraint("variant_id", "location_id"),
    CheckConstraint("on_hand >= 0", name="on_hand_nonnegative"),
    CheckConstraint(
        "reserved >= 0 AND reserved <= on_hand",
        name="reserved_valid",
    ),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    variant_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("product_variants.id"),nullable=False)
    location_id: Mapped[int]=mapped_column(ForeignKey("inventory_locations.id"),nullable=False)
    on_hand: Mapped[int]=mapped_column(Integer,default=0,nullable=False)
    reserved: Mapped[int]=mapped_column(Integer,default=0,nullable=False)
    variant: Mapped[ProductVariant]=relationship(back_populates="inventory")
    location: Mapped[InventoryLocation]=relationship(back_populates="inventory")
class InventoryMovement(Base, AuditMixin):
    __tablename__="inventory_movements"
    __table_args__ = (
    CheckConstraint("quantity_delta <> 0", name="quantity_delta_nonzero"),
    Index("ix_inventory_movement_variant_created", "variant_id", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    variant_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("product_variants.id"),nullable=False)
    location_id: Mapped[int]=mapped_column(ForeignKey("inventory_locations.id"),nullable=False)
    quantity_delta: Mapped[int]=mapped_column(Integer,nullable=False)
    reason: Mapped[str]=mapped_column(String(80),nullable=False)
    reference_type: Mapped[Optional[str]]=mapped_column(String(80))
    reference_id: Mapped[Optional[uuid.UUID]]=mapped_column(UUID(as_uuid=True))
    variant: Mapped[ProductVariant]=relationship(back_populates="movements")
    location: Mapped[InventoryLocation]=relationship()
class Cart(Base, AuditMixin):
    __tablename__="carts"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("users.id"))
    guest_token_hash: Mapped[Optional[str]]=mapped_column(String(128))
    expires_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    user: Mapped[Optional[User]]=relationship(back_populates="carts",foreign_keys=[user_id])
    items: Mapped[List["CartItem"]]=relationship(back_populates="cart",foreign_keys="CartItem.cart_id")
class CartItem(Base, AuditMixin):
    __tablename__="cart_items"
    __table_args__ = (
    UniqueConstraint("cart_id", "variant_id"),
    CheckConstraint("quantity > 0", name="quantity_positive"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    cart_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("carts.id"),nullable=False)
    variant_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("product_variants.id"),nullable=False)
    quantity: Mapped[int]=mapped_column(Integer,default=1,nullable=False)
    cart: Mapped[Cart]=relationship(back_populates="items",foreign_keys=[cart_id])
    variant: Mapped[ProductVariant]=relationship(back_populates="cart_items")
class Discount(Base, AuditMixin):
    __tablename__="discounts"
    __table_args__ = (
    Index(
        "uq_discount_code_active",
        "code_normalized",
        unique=True,
        postgresql_where=text("deleted_at IS NULL"),
    ),
    CheckConstraint("value > 0", name="value_positive"),
    CheckConstraint(
        "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
        name="valid_date_range",
    ),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    code: Mapped[str]=mapped_column(String(80),nullable=False)
    code_normalized: Mapped[str]=mapped_column(String(80),nullable=False)
    discount_type: Mapped[DiscountType]=mapped_column(Enum(DiscountType,name="discount_type", values_callable=lambda enum_cls: [member.value for member in enum_cls],),nullable=False)
    value: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    currency: Mapped[Optional[str]]=mapped_column(String(3))
    starts_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    ends_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    usage_limit: Mapped[Optional[int]]=mapped_column(Integer)
    per_user_limit: Mapped[Optional[int]]=mapped_column(Integer)
    is_active: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
    products: Mapped[List["DiscountProduct"]]=relationship(back_populates="discount")
    redemptions: Mapped[List["DiscountRedemption"]]=relationship(back_populates="discount")
    order_links: Mapped[List["OrderDiscount"]]=relationship(back_populates="discount")
class DiscountProduct(Base, AuditMixin):
    __tablename__="discount_products"
    __table_args__=(UniqueConstraint("discount_id","product_id"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    discount_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("discounts.id"),nullable=False)
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id"),nullable=False)
    discount: Mapped[Discount]=relationship(back_populates="products")
    product: Mapped[Product]=relationship()
class DiscountCategory(Base, AuditMixin):
    __tablename__="discount_categories"
    __table_args__=(UniqueConstraint("discount_id","category_id"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    discount_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("discounts.id"),nullable=False)
    category_id: Mapped[int]=mapped_column(ForeignKey("categories.id"),nullable=False)
    discount: Mapped[Discount]=relationship()
    category: Mapped[Category]=relationship()
class Order(Base, AuditMixin):
    __tablename__="orders"
    __table_args__ = (
    Index("ix_orders_user_created", "user_id", "created_at"),
    CheckConstraint(
        "subtotal_amount >= 0 AND shipping_amount >= 0 "
        "AND tax_amount >= 0 AND discount_amount >= 0 "
        "AND total_amount >= 0",
        name="amounts_nonnegative",
    ),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    order_number: Mapped[str]=mapped_column(String(40),unique=True,nullable=False)
    user_id: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("users.id"))
    status: Mapped[OrderStatus]=mapped_column(Enum(OrderStatus,name="order_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),default=OrderStatus.PENDING,nullable=False)
    currency: Mapped[str]=mapped_column(String(3),default="INR",nullable=False)
    subtotal_amount: Mapped[Decimal]=mapped_column(Numeric(12,2),default=Decimal("0"),nullable=False)
    shipping_amount: Mapped[Decimal]=mapped_column(Numeric(12,2),default=Decimal("0"),nullable=False)
    tax_amount: Mapped[Decimal]=mapped_column(Numeric(12,2),default=Decimal("0"),nullable=False)
    discount_amount: Mapped[Decimal]=mapped_column(Numeric(12,2),default=Decimal("0"),nullable=False)
    total_amount: Mapped[Decimal]=mapped_column(Numeric(12,2),default=Decimal("0"),nullable=False)
    shipping_address_snapshot: Mapped[dict]=mapped_column(JSONB,nullable=False)
    billing_address_snapshot: Mapped[Optional[dict]]=mapped_column(JSONB)
    customer_email_snapshot: Mapped[Optional[str]]=mapped_column(String(320))
    user: Mapped[Optional[User]]=relationship(back_populates="orders",foreign_keys=[user_id])
    items: Mapped[List["OrderItem"]]=relationship(back_populates="order",foreign_keys="OrderItem.order_id")
    payments: Mapped[List["Payment"]]=relationship(back_populates="order",foreign_keys="Payment.order_id")
    shipments: Mapped[List["Shipment"]]=relationship(back_populates="order")
    discounts: Mapped[List["OrderDiscount"]]=relationship(back_populates="order")
    redemptions: Mapped[List["DiscountRedemption"]]=relationship(back_populates="order")
    status_history: Mapped[List["OrderStatusHistory"]]=relationship(back_populates="order")
    subscription_link: Mapped[Optional["SubscriptionOrder"]]=relationship(back_populates="order",uselist=False)
class OrderItem(Base, AuditMixin):
    __tablename__="order_items"
    __table_args__ = (
    CheckConstraint("quantity > 0", name="quantity_positive"),
    CheckConstraint("unit_price >= 0", name="unit_price_nonnegative"),
    Index("ix_order_items_order", "order_id"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("orders.id"),nullable=False)
    variant_id: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("product_variants.id"))
    sku_snapshot: Mapped[str]=mapped_column(String(100),nullable=False)
    name_snapshot: Mapped[str]=mapped_column(String(240),nullable=False)
    unit_price: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    quantity: Mapped[int]=mapped_column(Integer,nullable=False)
    product_snapshot: Mapped[Optional[dict]]=mapped_column(JSONB)
    order: Mapped[Order]=relationship(back_populates="items",foreign_keys=[order_id])
    variant: Mapped[Optional[ProductVariant]]=relationship(back_populates="order_items")
class Payment(Base, AuditMixin):
    __tablename__="payments"
    __table_args__ = (
    CheckConstraint("amount >= 0", name="amount_nonnegative"),
    Index("ix_payments_order_status", "order_id", "status"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("orders.id"),nullable=False)
    provider: Mapped[str]=mapped_column(String(80),nullable=False)
    provider_reference: Mapped[Optional[str]]=mapped_column(String(255))
    idempotency_key: Mapped[Optional[str]]=mapped_column(String(255),unique=True)
    status: Mapped[PaymentStatus]=mapped_column(Enum(PaymentStatus,name="payment_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),default=PaymentStatus.PENDING,nullable=False)
    amount: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    currency: Mapped[str]=mapped_column(String(3),default="INR",nullable=False)
    provider_payload: Mapped[Optional[dict]]=mapped_column(JSONB)
    order: Mapped[Order]=relationship(back_populates="payments",foreign_keys=[order_id])
class Shipment(Base, AuditMixin):
    __tablename__="shipments"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("orders.id"),nullable=False)
    carrier: Mapped[Optional[str]]=mapped_column(String(100))
    tracking_number: Mapped[Optional[str]]=mapped_column(String(160))
    status: Mapped[str]=mapped_column(String(40),default="pending",nullable=False)
    shipped_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    order: Mapped[Order]=relationship(back_populates="shipments")
class DiscountRedemption(Base, AuditMixin):
    __tablename__="discount_redemptions"
    __table_args__=(UniqueConstraint("discount_id","order_id"),Index("ix_redemption_user_discount","user_id","discount_id"))
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    discount_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("discounts.id"),nullable=False)
    order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("orders.id"),nullable=False)
    user_id: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    discount: Mapped[Discount]=relationship(back_populates="redemptions")
    order: Mapped[Order]=relationship(back_populates="redemptions")
    user: Mapped[Optional[User]]=relationship(foreign_keys=[user_id])
class OrderDiscount(Base, AuditMixin):
    __tablename__="order_discounts"
    __table_args__=(UniqueConstraint("order_id","discount_id"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("orders.id"),nullable=False)
    discount_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("discounts.id"),nullable=False)
    applied_amount: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=False)
    order: Mapped[Order]=relationship(back_populates="discounts")
    discount: Mapped[Discount]=relationship(back_populates="order_links")
class OrderStatusHistory(Base, AuditMixin):
    __tablename__="order_status_history"
    __table_args__=(Index("ix_order_history_order_created","order_id","created_at"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("orders.id"),nullable=False)
    old_status: Mapped[Optional[str]]=mapped_column(String(40))
    new_status: Mapped[str]=mapped_column(String(40),nullable=False)
    reason: Mapped[Optional[str]]=mapped_column(Text)
    order: Mapped[Order]=relationship(back_populates="status_history")
class DogBreed(Base, AuditMixin):
    __tablename__="dog_breeds"
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    name: Mapped[str]=mapped_column(String(160),unique=True,nullable=False)
    size_group: Mapped[Optional[str]]=mapped_column(String(40))
    dogs: Mapped[List["DogProfile"]]=relationship(back_populates="breed")
class DogProfile(Base, AuditMixin):
    __tablename__="dog_profiles"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id"),nullable=False)
    breed_id: Mapped[Optional[int]]=mapped_column(ForeignKey("dog_breeds.id"))
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    birth_date: Mapped[Optional[date]]=mapped_column(Date)
    weight_kg: Mapped[Optional[Decimal]]=mapped_column(Numeric(6,2))
    sex: Mapped[Optional[str]]=mapped_column(String(20))
    notes: Mapped[Optional[str]]=mapped_column(Text)
    user: Mapped[User]=relationship(back_populates="dogs",foreign_keys=[user_id])
    breed: Mapped[Optional[DogBreed]]=relationship(back_populates="dogs")
    dietary_links: Mapped[List["DogDietaryNeed"]]=relationship(back_populates="dog")
class DietaryNeed(Base, AuditMixin):
    __tablename__="dietary_needs"
    id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    name: Mapped[str]=mapped_column(String(120),unique=True,nullable=False)
    description: Mapped[Optional[str]]=mapped_column(Text)
    dog_links: Mapped[List["DogDietaryNeed"]]=relationship(back_populates="need")
class DogDietaryNeed(Base, AuditMixin):
    __tablename__="dog_dietary_needs"
    __table_args__=(UniqueConstraint("dog_id","dietary_need_id"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    dog_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("dog_profiles.id"),nullable=False)
    dietary_need_id: Mapped[int]=mapped_column(ForeignKey("dietary_needs.id"),nullable=False)
    dog: Mapped[DogProfile]=relationship(back_populates="dietary_links")
    need: Mapped[DietaryNeed]=relationship(back_populates="dog_links")
class Subscription(Base, AuditMixin):
    __tablename__="subscriptions"
    __table_args__=(Index("ix_subscriptions_due","next_billing_at",postgresql_where=text("status = 'active' AND deleted_at IS NULL")),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id"),nullable=False)
    status: Mapped[SubscriptionStatus]=mapped_column(Enum(SubscriptionStatus,name="subscription_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),default=SubscriptionStatus.ACTIVE,nullable=False)
    billing_interval: Mapped[str]=mapped_column(String(32),default="monthly",nullable=False)
    next_billing_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    provider_subscription_id: Mapped[Optional[str]]=mapped_column(String(255),unique=True)
    payment_method_reference: Mapped[Optional[str]]=mapped_column(String(255))
    user: Mapped[User]=relationship(back_populates="subscriptions",foreign_keys=[user_id])
    items: Mapped[List["SubscriptionItem"]]=relationship(back_populates="subscription")
    generated_orders: Mapped[List["SubscriptionOrder"]]=relationship(back_populates="subscription")
class SubscriptionItem(Base, AuditMixin):
    __tablename__="subscription_items"
    __table_args__ = (
    UniqueConstraint("subscription_id", "variant_id"),
    CheckConstraint("quantity > 0", name="quantity_positive"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("subscriptions.id"),nullable=False)
    variant_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("product_variants.id"),nullable=False)
    quantity: Mapped[int]=mapped_column(Integer,default=1,nullable=False)
    subscription: Mapped[Subscription]=relationship(back_populates="items")
    variant: Mapped[ProductVariant]=relationship(back_populates="subscription_items")
class SubscriptionOrder(Base, AuditMixin):
    __tablename__="subscription_orders"
    __table_args__=(UniqueConstraint("subscription_id","order_id"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("subscriptions.id"),nullable=False)
    order_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("orders.id"),nullable=False,unique=True)
    billing_period_start: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    billing_period_end: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    subscription: Mapped[Subscription]=relationship(back_populates="generated_orders")
    order: Mapped[Order]=relationship(back_populates="subscription_link")
class Review(Base, AuditMixin):
    __tablename__="reviews"
    __table_args__ = (
    CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    Index(
        "ix_reviews_product_status_created",
        "product_id",
        "moderation_status",
        "created_at",
    ),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id"),nullable=False)
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id"),nullable=False)
    rating: Mapped[int]=mapped_column(Integer,nullable=False)
    title: Mapped[Optional[str]]=mapped_column(String(180))
    body: Mapped[Optional[str]]=mapped_column(Text)
    moderation_status: Mapped[str]=mapped_column(String(32),default="pending",nullable=False)
    verified_purchase: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
    user: Mapped[User]=relationship(back_populates="reviews",foreign_keys=[user_id])
    product: Mapped[Product]=relationship(back_populates="reviews")
class CMSPage(Base, AuditMixin):
    __tablename__="cms_pages"
    __table_args__=(Index("uq_cms_slug_active","slug",unique=True,postgresql_where=text("deleted_at IS NULL")),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    slug: Mapped[str]=mapped_column(String(180),nullable=False)
    title: Mapped[str]=mapped_column(String(240),nullable=False)
    status: Mapped[ContentStatus]=mapped_column(Enum(ContentStatus,name="content_status", values_callable=lambda enum_cls: [member.value for member in enum_cls],),default=ContentStatus.DRAFT,nullable=False)
    current_published_version_id: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("cms_page_versions.id",use_alter=True,name="fk_cms_page_published_version"))
    versions: Mapped[List["CMSPageVersion"]]=relationship(back_populates="page",foreign_keys="CMSPageVersion.page_id")
    current_published_version: Mapped[Optional["CMSPageVersion"]]=relationship(foreign_keys=[current_published_version_id],post_update=True)
class CMSPageVersion(Base, AuditMixin):
    __tablename__="cms_page_versions"
    __table_args__=(UniqueConstraint("page_id","version_number"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    page_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("cms_pages.id"),nullable=False)
    version_number: Mapped[int]=mapped_column(Integer,nullable=False)
    content: Mapped[dict]=mapped_column(JSONB,nullable=False)
    change_summary: Mapped[Optional[str]]=mapped_column(String(500))
    edited_by: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("users.id"))
    published_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    page: Mapped[CMSPage]=relationship(back_populates="versions",foreign_keys=[page_id])
    editor: Mapped[Optional[User]]=relationship(foreign_keys=[edited_by])
class FAQItem(Base, AuditMixin):
    __tablename__="faq_items"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    question: Mapped[str]=mapped_column(String(500),nullable=False)
    answer: Mapped[str]=mapped_column(Text,nullable=False)
    category: Mapped[Optional[str]]=mapped_column(String(120))
    display_order: Mapped[int]=mapped_column(Integer,default=0,nullable=False)
    is_published: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
class Wishlist(Base, AuditMixin):
    __tablename__="wishlists"
    __table_args__=(UniqueConstraint("user_id","name"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id"),nullable=False)
    name: Mapped[str]=mapped_column(String(120),default="My wishlist",nullable=False)
    items: Mapped[List["WishlistItem"]]=relationship(back_populates="wishlist")
class WishlistItem(Base, AuditMixin):
    __tablename__="wishlist_items"
    __table_args__=(UniqueConstraint("wishlist_id","product_id"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    wishlist_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("wishlists.id"),nullable=False)
    product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id"),nullable=False)
    wishlist: Mapped[Wishlist]=relationship(back_populates="items")
    product: Mapped[Product]=relationship()
class IdempotencyKey(Base, AuditMixin):
    __tablename__="idempotency_keys"
    __table_args__=(UniqueConstraint("scope","key"),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    scope: Mapped[str]=mapped_column(String(120),nullable=False)
    key: Mapped[str]=mapped_column(String(255),nullable=False)
    request_hash: Mapped[str]=mapped_column(String(64),nullable=False)
    response_reference: Mapped[Optional[str]]=mapped_column(String(255))
    expires_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]]=mapped_column(ForeignKey("users.id"))
    actor_type: Mapped[str]=mapped_column(String(32),default="user",nullable=False)
    action: Mapped[str]=mapped_column(String(120),nullable=False)
    target_type: Mapped[str]=mapped_column(String(120),nullable=False)
    target_id: Mapped[Optional[str]]=mapped_column(String(120))
    request_id: Mapped[Optional[str]]=mapped_column(String(120))
    ip_address: Mapped[Optional[str]]=mapped_column(String(64))
    details: Mapped[Optional[dict]]=mapped_column(JSONB)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    actor: Mapped[Optional[User]]=relationship(foreign_keys=[actor_id])
class OutboxEvent(Base):
    __tablename__="outbox_events"
    __table_args__=(Index("ix_outbox_pending","created_at",postgresql_where=text("published_at IS NULL")),)
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    event_type: Mapped[str]=mapped_column(String(160),nullable=False)
    aggregate_type: Mapped[str]=mapped_column(String(120),nullable=False)
    aggregate_id: Mapped[str]=mapped_column(String(120),nullable=False)
    payload: Mapped[dict]=mapped_column(JSONB,nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    published_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int]=mapped_column(Integer,default=0,nullable=False)
    next_attempt_at: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]]=mapped_column(Text)
