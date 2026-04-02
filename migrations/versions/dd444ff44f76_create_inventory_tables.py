"""create inventory tables

Revision ID: cc333ff33e65
Revises: bb222ee22d54
Create Date: 2026-07-10 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "dd444ff44f76"
down_revision: str | None = "cc333ff33e65"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
	# --- pg_trgm extension for trigram search ---
	op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

	# --- warehouse ---
	op.create_table(
		"warehouse",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("name", sa.String(300), nullable=False),
		sa.Column("code", sa.String(50), nullable=False),
		sa.Column("location", sa.String(500), nullable=True),
		sa.Column("address", sa.String(500), nullable=True),
		sa.Column("contact_email", sa.String(255), nullable=True),
		sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_warehouse")),
	)
	op.create_index(op.f("ix_warehouse_tenant_id"), "warehouse", ["tenant_id"])
	op.create_index(
		"uq_warehouse_tenant_code",
		"warehouse",
		["tenant_id", "code"],
		unique=True,
	)

	# --- product ---
	op.create_table(
		"product",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("code", sa.String(100), nullable=False),
		sa.Column("name", sa.String(500), nullable=False),
		sa.Column("category", sa.String(200), nullable=True),
		sa.Column("description", sa.Text(), nullable=True),
		sa.Column("unit", sa.String(50), nullable=False, server_default="pcs"),
		sa.Column("status", sa.String(20), nullable=False, server_default="active"),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.Column(
			"updated_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_product")),
	)
	# Add tsvector column via raw DDL (no SA type mapping needed)
	op.execute(
		"ALTER TABLE product ADD COLUMN search_vector tsvector"
	)
	op.create_index(op.f("ix_product_tenant_id"), "product", ["tenant_id"])
	op.create_index(
		"uq_product_tenant_code",
		"product",
		["tenant_id", "code"],
		unique=True,
	)
	op.execute(
		"CREATE INDEX ix_product_search_vector ON product USING GIN (search_vector)"
	)
	op.execute(
		"CREATE INDEX ix_product_name_trgm ON product "
		"USING GIN (name gin_trgm_ops)"
	)
	# Auto-update search_vector trigger
	op.execute("""
		CREATE OR REPLACE FUNCTION product_search_vector_update() RETURNS trigger AS $$
		BEGIN
			NEW.search_vector :=
				setweight(to_tsvector('simple', COALESCE(NEW.code, '')), 'A') ||
				setweight(to_tsvector('simple', COALESCE(NEW.name, '')), 'B') ||
				setweight(to_tsvector('simple', COALESCE(NEW.category, '')), 'C') ||
				setweight(to_tsvector('simple', COALESCE(NEW.description, '')), 'D');
			RETURN NEW;
		END;
		$$ LANGUAGE plpgsql;
	""")
	op.execute("""
		CREATE TRIGGER trg_product_search_vector
		BEFORE INSERT OR UPDATE ON product
		FOR EACH ROW EXECUTE FUNCTION product_search_vector_update();
	""")

	# --- supplier ---
	op.create_table(
		"supplier",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("name", sa.String(300), nullable=False),
		sa.Column("contact_email", sa.String(255), nullable=True),
		sa.Column("phone", sa.String(50), nullable=True),
		sa.Column("address", sa.String(500), nullable=True),
		sa.Column("default_lead_time_days", sa.Integer(), nullable=True),
		sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier")),
	)
	op.create_index(op.f("ix_supplier_tenant_id"), "supplier", ["tenant_id"])

	# --- inventory_stock ---
	op.create_table(
		"inventory_stock",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("product_id", UUID(as_uuid=True), nullable=False),
		sa.Column("warehouse_id", UUID(as_uuid=True), nullable=False),
		sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="0"),
		sa.Column(
			"updated_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_stock")),
		sa.ForeignKeyConstraint(
			["product_id"], ["product.id"],
			name=op.f("fk_inventory_stock_product_id_product"),
		),
		sa.ForeignKeyConstraint(
			["warehouse_id"], ["warehouse.id"],
			name=op.f("fk_inventory_stock_warehouse_id_warehouse"),
		),
	)
	op.create_index(op.f("ix_inventory_stock_tenant_id"), "inventory_stock", ["tenant_id"])
	op.create_index(
		"uq_inventory_stock_tenant_product_warehouse",
		"inventory_stock",
		["tenant_id", "product_id", "warehouse_id"],
		unique=True,
	)
	op.create_index(
		"ix_inventory_stock_warehouse_product",
		"inventory_stock",
		["warehouse_id", "product_id"],
	)

	# --- stock_adjustment ---
	reason_code_enum = sa.Enum(
		"received",
		"damaged",
		"returned",
		"correction",
		"other",
		"supplier_delivery",
		"transfer_out",
		"transfer_in",
		name="reason_code_enum",
	)
	op.create_table(
		"stock_adjustment",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("product_id", UUID(as_uuid=True), nullable=False),
		sa.Column("warehouse_id", UUID(as_uuid=True), nullable=False),
		sa.Column("quantity_change", sa.Integer(), nullable=False),
		sa.Column("reason_code", reason_code_enum, nullable=False),
		sa.Column("actor_id", sa.String(100), nullable=False),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.Column("transfer_id", UUID(as_uuid=True), nullable=True),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_adjustment")),
		sa.ForeignKeyConstraint(
			["product_id"], ["product.id"],
			name=op.f("fk_stock_adjustment_product_id_product"),
		),
		sa.ForeignKeyConstraint(
			["warehouse_id"], ["warehouse.id"],
			name=op.f("fk_stock_adjustment_warehouse_id_warehouse"),
		),
	)
	op.create_index(
		op.f("ix_stock_adjustment_tenant_id"),
		"stock_adjustment",
		["tenant_id"],
	)

	# --- stock_transfer_history ---
	op.create_table(
		"stock_transfer_history",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("product_id", UUID(as_uuid=True), nullable=False),
		sa.Column("from_warehouse_id", UUID(as_uuid=True), nullable=False),
		sa.Column("to_warehouse_id", UUID(as_uuid=True), nullable=False),
		sa.Column("quantity", sa.Integer(), nullable=False),
		sa.Column("actor_id", sa.String(100), nullable=False),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_stock_transfer_history")),
		sa.ForeignKeyConstraint(
			["product_id"], ["product.id"],
			name=op.f("fk_stock_transfer_history_product_id_product"),
		),
		sa.ForeignKeyConstraint(
			["from_warehouse_id"], ["warehouse.id"],
			name=op.f("fk_stock_transfer_history_from_warehouse_id_warehouse"),
		),
		sa.ForeignKeyConstraint(
			["to_warehouse_id"], ["warehouse.id"],
			name=op.f("fk_stock_transfer_history_to_warehouse_id_warehouse"),
		),
	)
	op.create_index(
		op.f("ix_stock_transfer_history_tenant_id"),
		"stock_transfer_history",
		["tenant_id"],
	)

	# --- reorder_alert ---
	alert_status_enum = sa.Enum(
		"pending", "acknowledged", "resolved",
		name="alert_status_enum",
	)
	op.create_table(
		"reorder_alert",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("product_id", UUID(as_uuid=True), nullable=False),
		sa.Column("warehouse_id", UUID(as_uuid=True), nullable=False),
		sa.Column("current_stock", sa.Integer(), nullable=False),
		sa.Column("reorder_point", sa.Integer(), nullable=False),
		sa.Column(
			"status",
			alert_status_enum,
			nullable=False,
			server_default="pending",
		),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("acknowledged_by", sa.String(100), nullable=True),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_reorder_alert")),
		sa.ForeignKeyConstraint(
			["product_id"], ["product.id"],
			name=op.f("fk_reorder_alert_product_id_product"),
		),
		sa.ForeignKeyConstraint(
			["warehouse_id"], ["warehouse.id"],
			name=op.f("fk_reorder_alert_warehouse_id_warehouse"),
		),
	)
	op.create_index(op.f("ix_reorder_alert_tenant_id"), "reorder_alert", ["tenant_id"])
	op.create_index(
		"uq_reorder_alert_tenant_product_warehouse",
		"reorder_alert",
		["tenant_id", "product_id", "warehouse_id"],
		unique=True,
	)

	# --- audit_log ---
	op.create_table(
		"audit_log",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("actor_id", sa.String(100), nullable=False),
		sa.Column("actor_type", sa.String(20), nullable=False, server_default="user"),
		sa.Column("action", sa.String(100), nullable=False),
		sa.Column("entity_type", sa.String(100), nullable=False),
		sa.Column("entity_id", sa.String(100), nullable=False),
		sa.Column("before_state", JSON, nullable=True),
		sa.Column("after_state", JSON, nullable=True),
		sa.Column("correlation_id", sa.String(100), nullable=True),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
	)
	op.create_index(op.f("ix_audit_log_tenant_id"), "audit_log", ["tenant_id"])

	# --- supplier_order ---
	supplier_order_status_enum = sa.Enum(
		"pending", "confirmed", "shipped",
		"partially_received", "received", "cancelled",
		name="supplier_order_status_enum",
	)
	op.create_table(
		"supplier_order",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("tenant_id", sa.String(50), nullable=False),
		sa.Column("supplier_id", UUID(as_uuid=True), nullable=False),
		sa.Column("order_number", sa.String(100), nullable=False),
		sa.Column(
			"status",
			supplier_order_status_enum,
			nullable=False,
			server_default="pending",
		),
		sa.Column("order_date", sa.Date(), nullable=False),
		sa.Column("expected_arrival_date", sa.Date(), nullable=True),
		sa.Column("received_date", sa.Date(), nullable=True),
		sa.Column("created_by", sa.String(100), nullable=False),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.Column(
			"updated_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.func.now(),
		),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_order")),
		sa.ForeignKeyConstraint(
			["supplier_id"], ["supplier.id"],
			name=op.f("fk_supplier_order_supplier_id_supplier"),
		),
	)
	op.create_index(op.f("ix_supplier_order_tenant_id"), "supplier_order", ["tenant_id"])
	op.create_index(
		"ix_supplier_order_status_date",
		"supplier_order",
		["status", "created_at"],
	)

	# --- supplier_order_line ---
	op.create_table(
		"supplier_order_line",
		sa.Column("id", UUID(as_uuid=True), nullable=False),
		sa.Column("order_id", UUID(as_uuid=True), nullable=False),
		sa.Column("product_id", UUID(as_uuid=True), nullable=False),
		sa.Column("warehouse_id", UUID(as_uuid=True), nullable=False),
		sa.Column("quantity_ordered", sa.Integer(), nullable=False),
		sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_order_line")),
		sa.ForeignKeyConstraint(
			["order_id"], ["supplier_order.id"],
			name=op.f("fk_supplier_order_line_order_id_supplier_order"),
		),
		sa.ForeignKeyConstraint(
			["product_id"], ["product.id"],
			name=op.f("fk_supplier_order_line_product_id_product"),
		),
		sa.ForeignKeyConstraint(
			["warehouse_id"], ["warehouse.id"],
			name=op.f("fk_supplier_order_line_warehouse_id_warehouse"),
		),
	)


def downgrade() -> None:
	op.drop_table("supplier_order_line")
	op.drop_index("ix_supplier_order_status_date", table_name="supplier_order")
	op.drop_index(op.f("ix_supplier_order_tenant_id"), table_name="supplier_order")
	op.drop_table("supplier_order")

	op.drop_index(op.f("ix_audit_log_tenant_id"), table_name="audit_log")
	op.drop_table("audit_log")

	op.drop_index(
		"uq_reorder_alert_tenant_product_warehouse",
		table_name="reorder_alert",
	)
	op.drop_index(op.f("ix_reorder_alert_tenant_id"), table_name="reorder_alert")
	op.drop_table("reorder_alert")

	op.drop_index(
		op.f("ix_stock_transfer_history_tenant_id"),
		table_name="stock_transfer_history",
	)
	op.drop_table("stock_transfer_history")

	op.drop_index(
		op.f("ix_stock_adjustment_tenant_id"),
		table_name="stock_adjustment",
	)
	op.drop_table("stock_adjustment")
	op.execute("DROP TYPE IF EXISTS reason_code_enum")

	op.drop_index(
		"uq_inventory_stock_tenant_product_warehouse",
		table_name="inventory_stock",
	)
	op.drop_index(op.f("ix_inventory_stock_tenant_id"), table_name="inventory_stock")
	op.drop_table("inventory_stock")

	op.execute("DROP TRIGGER IF EXISTS trg_product_search_vector ON product")
	op.execute("DROP FUNCTION IF EXISTS product_search_vector_update()")
	op.execute("DROP INDEX IF EXISTS ix_product_name_trgm")
	op.execute("DROP INDEX IF EXISTS ix_product_search_vector")
	op.drop_index("uq_product_tenant_code", table_name="product")
	op.drop_index(op.f("ix_product_tenant_id"), table_name="product")
	op.drop_table("product")

	op.drop_index("uq_warehouse_tenant_code", table_name="warehouse")
	op.drop_index(op.f("ix_warehouse_tenant_id"), table_name="warehouse")
	op.drop_table("warehouse")

	op.drop_index(op.f("ix_supplier_tenant_id"), table_name="supplier")
	op.drop_table("supplier")

	op.execute("DROP TYPE IF EXISTS alert_status_enum")
	op.execute("DROP TYPE IF EXISTS supplier_order_status_enum")
