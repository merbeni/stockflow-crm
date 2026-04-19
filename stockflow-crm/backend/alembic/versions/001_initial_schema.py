"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ENUM types are created automatically by SQLAlchemy the first time each
    # table that uses them is created. No manual CREATE TYPE needed.

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "operator", name="userrole"),
            nullable=False,
            server_default="operator",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_customers_email"),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("current_stock", sa.Numeric(10, 3), nullable=False, server_default="0"),
        sa.Column("minimum_stock", sa.Numeric(10, 3), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "shipped", "delivered", name="orderstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("gemini_raw", JSONB(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "confirmed", "rejected", name="invoicestatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "confidence",
            sa.Enum("high", "medium", "low", name="confidencelevel"),
            nullable=False,
        ),
        sa.Column("supplier_sku", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_items_supplier_sku", "invoice_items", ["supplier_sku"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column(
            "type",
            sa.Enum("entry", "exit", "adjustment", name="movementtype"),
            nullable=False,
        ),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "product_supplier_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("supplier_sku", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "supplier_sku", name="uq_supplier_sku"),
    )


def downgrade() -> None:
    op.drop_table("product_supplier_mappings")
    op.drop_table("stock_movements")
    op.drop_table("order_items")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("suppliers")
    op.drop_table("customers")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS movementtype")
    op.execute("DROP TYPE IF EXISTS confidencelevel")
    op.execute("DROP TYPE IF EXISTS invoicestatus")
    op.execute("DROP TYPE IF EXISTS userrole")
