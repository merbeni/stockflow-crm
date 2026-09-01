"""multi_tenancy: organizations, contacto y verificacion de usuarios,
stock decimal por producto

Revision ID: a1b2c3d4e5f6
Revises: 956790fe30cc
Create Date: 2026-08-31

Estrategia de backfill: las columnas ``organization_id`` se crean primero como
nullable, se asignan todas las filas existentes a una organización "Default" y
recién entonces se imponen el NOT NULL y las nuevas restricciones de unicidad.
De ese modo la migración no pierde los datos previos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "956790fe30cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tablas raíz que pasan a estar aisladas por organización.
_TENANT_TABLES = (
    "users",
    "products",
    "suppliers",
    "customers",
    "orders",
    "invoices",
    "stock_movements",
    "product_supplier_mappings",
)


def upgrade() -> None:
    bind = op.get_bind()

    # ── 1. tabla de organizaciones ───────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # ── 2. columnas nullable + backfill ──────────────────────────────────────
    for table in _TENANT_TABLES:
        op.add_column(table, sa.Column("organization_id", sa.Integer(), nullable=True))

    # Solo se crea la organización por defecto si ya hay datos que migrar.
    has_rows = False
    for table in _TENANT_TABLES:
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar()
        if count:
            has_rows = True
            break

    if has_rows:
        bind.execute(
            sa.text(
                "INSERT INTO organizations (name, slug) VALUES ('Default', 'default')"
            )
        )
        default_id = bind.execute(
            sa.text("SELECT id FROM organizations WHERE slug = 'default'")
        ).scalar()
        for table in _TENANT_TABLES:
            bind.execute(
                sa.text(f"UPDATE {table} SET organization_id = :oid"),
                {"oid": default_id},
            )

    # ── 3. NOT NULL, índices y claves foráneas ───────────────────────────────
    for table in _TENANT_TABLES:
        op.alter_column(table, "organization_id", existing_type=sa.Integer(), nullable=False)
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
        op.create_foreign_key(
            f"fk_{table}_organization_id",
            table,
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # ── 4. unicidad ahora por organización ───────────────────────────────────
    # El SKU y el correo del cliente eran únicos a nivel global; con varias
    # empresas en el mismo sistema eso deja de tener sentido.
    with op.batch_alter_table("products") as batch:
        batch.drop_index("ix_products_sku")
        batch.create_index("ix_products_sku", ["sku"], unique=False)
        batch.create_unique_constraint("uq_product_org_sku", ["organization_id", "sku"])

    with op.batch_alter_table("customers") as batch:
        batch.create_unique_constraint(
            "uq_customer_org_email", ["organization_id", "email"]
        )

    # ── 5. datos de contacto y verificación de correo ────────────────────────
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    op.add_column(
        "users", sa.Column("email_verification_token", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verification_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_index(
        "ix_users_email_verification_token", "users", ["email_verification_token"]
    )
    # Los usuarios que ya existían quedan verificados: de lo contrario no
    # podrían volver a entrar tras la actualización.
    op.execute("UPDATE users SET is_email_verified = true")

    # ── 6. stock decimal opcional por producto ───────────────────────────────
    op.add_column(
        "products",
        sa.Column(
            "allow_decimal_stock", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    # Un producto cuyo stock actual o mínimo ya tenía decimales se marca como
    # "a granel" para no invalidar datos existentes.
    op.execute(
        "UPDATE products SET allow_decimal_stock = true "
        "WHERE current_stock <> ROUND(current_stock) OR minimum_stock <> ROUND(minimum_stock)"
    )


def downgrade() -> None:
    op.drop_column("products", "allow_decimal_stock")

    op.drop_index("ix_users_email_verification_token", table_name="users")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "is_email_verified")
    op.drop_column("users", "is_active")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")

    with op.batch_alter_table("customers") as batch:
        batch.drop_constraint("uq_customer_org_email", type_="unique")

    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("uq_product_org_sku", type_="unique")
        batch.drop_index("ix_products_sku")
        batch.create_index("ix_products_sku", ["sku"], unique=True)

    for table in _TENANT_TABLES:
        op.drop_constraint(f"fk_{table}_organization_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_column(table, "organization_id")

    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
