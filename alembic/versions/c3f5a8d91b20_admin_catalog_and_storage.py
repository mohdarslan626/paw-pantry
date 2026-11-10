"""add external fulfillment and media storage backend

Revision ID: c3f5a8d91b20
Revises: a7edf9879729
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c3f5a8d91b20"
down_revision: Union[str, Sequence[str], None] = "a7edf9879729"
branch_labels = None
depends_on = None


def upgrade() -> None:
    fulfillment = sa.Enum("internal", "external_link", name="product_fulfillment_type")
    marketplace = sa.Enum("amazon", "flipkart", "other", name="product_marketplace")
    storage = sa.Enum("local", "s3", name="storage_backend_type")
    bind = op.get_bind()
    fulfillment.create(bind, checkfirst=True)
    marketplace.create(bind, checkfirst=True)
    storage.create(bind, checkfirst=True)
    op.add_column("products", sa.Column("fulfillment_type", fulfillment, nullable=False, server_default="internal"))
    op.add_column("products", sa.Column("external_url", sa.String(length=2048), nullable=True))
    op.add_column("products", sa.Column("external_marketplace", marketplace, nullable=True))
    op.add_column("media_assets", sa.Column("storage_backend", storage, nullable=False, server_default="local"))
    op.alter_column("products", "fulfillment_type", server_default=None)
    op.alter_column("media_assets", "storage_backend", server_default=None)


def downgrade() -> None:
    op.drop_column("media_assets", "storage_backend")
    op.drop_column("products", "external_marketplace")
    op.drop_column("products", "external_url")
    op.drop_column("products", "fulfillment_type")
    bind = op.get_bind()
    sa.Enum(name="storage_backend_type").drop(bind, checkfirst=True)
    sa.Enum(name="product_marketplace").drop(bind, checkfirst=True)
    sa.Enum(name="product_fulfillment_type").drop(bind, checkfirst=True)
