"""Add manufacturing tables - BOM, Work Orders, Routing, Workstations, Production Planning, and OEE.

Revision ID: 2026_04_26_manufacturing
Revises: previous_head
Create Date: 2026-04-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "2026_04_26_manufacturing"
down_revision = None  # Set to actual parent revision in production
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BOM tables
    op.create_table(
        "bill_of_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("bom_quantity", sa.Numeric(19, 6), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(50), nullable=False, server_default="pcs"),
        sa.Column(
            "status",
            sa.Enum("draft", "submitted", "inactive", "superseded", name="bom_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("revision", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("supersedes_bom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("routing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_bom_tenant_product", "tenant_id", "product_id"),
        sa.Index("ix_bom_tenant_status", "tenant_id", "status"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
    )

    # Partial unique index: only one active BOM per tenant/product
    op.execute("""
        CREATE UNIQUE INDEX uq_bom_tenant_product_active
        ON bill_of_materials (tenant_id, product_id)
        WHERE is_active = true
    """)

    op.create_table(
        "bill_of_materials_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_code", sa.String(100), nullable=False),
        sa.Column("item_name", sa.String(300), nullable=False),
        sa.Column("required_quantity", sa.Numeric(19, 6), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False, server_default="pcs"),
        sa.Column("source_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_bom_item_tenant_bom", "tenant_id", "bom_id"),
        sa.ForeignKeyConstraint(["bom_id"], ["bill_of_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouse.id"], ondelete="SET NULL"),
    )

    # Work Order tables
    op.create_table(
        "work_order",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_snapshot", postgresql.JSON(), nullable=True),
        sa.Column("quantity", sa.Numeric(19, 6), nullable=False),
        sa.Column("produced_quantity", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("source_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("wip_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fg_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "submitted", "not_started", "in_progress",
                "completed", "stopped", "cancelled",
                name="work_order_status"
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "transfer_mode",
            sa.Enum("direct", "manufacture", name="wo_transfer_mode"),
            nullable=False,
            server_default="direct",
        ),
        sa.Column("planned_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_reason", sa.Text(), nullable=True),
        sa.Column("routing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("routing_snapshot", postgresql.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_wo_tenant_status", "tenant_id", "status"),
        sa.Index("ix_wo_tenant_product", "tenant_id", "product_id"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bom_id"], ["bill_of_materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouse.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wip_warehouse_id"], ["warehouse.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fg_warehouse_id"], ["warehouse.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "work_order_material_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_code", sa.String(100), nullable=False),
        sa.Column("item_name", sa.String(300), nullable=False),
        sa.Column("required_quantity", sa.Numeric(19, 6), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False, server_default="pcs"),
        sa.Column("source_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reserved_quantity", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("transferred_quantity", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("consumed_quantity", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_woml_wo_id", "work_order_id"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouse.id"], ondelete="SET NULL"),
    )

    # Workstation tables
    op.create_table(
        "workstation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "disabled", name="workstation_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("hourly_cost", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_ws_tenant_status", "tenant_id", "status"),
    )

    op.create_table(
        "workstation_working_hour",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(10), nullable=False),
        sa.Column("end_time", sa.String(10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstation.id"], ondelete="CASCADE"),
    )

    # Routing tables
    op.create_table(
        "routing",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "submitted", "inactive", name="routing_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_routing_tenant_status", "tenant_id", "status"),
    )

    op.create_table(
        "routing_operation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("routing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_name", sa.String(200), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("setup_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fixed_run_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("variable_run_minutes_per_unit", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("overlap_lag_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_routing_op_routing", "routing_id"),
        sa.ForeignKeyConstraint(["routing_id"], ["routing.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstation.id"], ondelete="SET NULL"),
    )

    # Production Planning tables
    op.create_table(
        "manufacturing_proposal",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("demand_source", sa.String(100), nullable=False),
        sa.Column("demand_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("demand_quantity", sa.Numeric(19, 6), nullable=False),
        sa.Column("proposed_quantity", sa.Numeric(19, 6), nullable=False),
        sa.Column("available_quantity", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("proposed", "accepted", "rejected", "stale", name="manufacturing_proposal_status"),
            nullable=False,
            server_default="proposed",
        ),
        sa.Column("decision", sa.String(50), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shortages", postgresql.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_mp_tenant_status", "tenant_id", "status"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bom_id"], ["bill_of_materials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "production_plan",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "reviewed", "firmed", "closed", name="production_plan_status"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("planning_strategy", sa.String(50), nullable=False, server_default="make_to_order"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("firmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("firmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_pp_tenant_status", "tenant_id", "status"),
    )

    op.create_table(
        "production_plan_line",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("routing_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sales_order_demand", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("forecast_demand", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("total_demand", sa.Numeric(19, 6), nullable=False),
        sa.Column("open_work_order_qty", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("available_stock", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("proposed_qty", sa.Numeric(19, 6), nullable=False),
        sa.Column("firmed_qty", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("completed_qty", sa.Numeric(19, 6), nullable=False, server_default="0"),
        sa.Column("shortage_summary", postgresql.JSON(), nullable=True),
        sa.Column("capacity_summary", postgresql.JSON(), nullable=True),
        sa.Column("idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_pp_line_plan", "plan_id"),
        sa.ForeignKeyConstraint(["plan_id"], ["production_plan.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bom_id"], ["bill_of_materials.id"], ondelete="SET NULL"),
    )

    # Downtime and OEE tables
    op.create_table(
        "downtime_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "reason",
            sa.Enum(
                "planned_maintenance", "unplanned_breakdown", "changeover",
                "material_shortage", "quality_hold",
                name="downtime_reason"
            ),
            nullable=False,
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_dt_tenant_workstation", "tenant_id", "workstation_id"),
        sa.Index("ix_dt_tenant_date", "tenant_id", "start_time"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "oee_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workstation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("record_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_production_time", sa.Integer(), nullable=False),
        sa.Column("stop_time", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_time", sa.Integer(), nullable=False),
        sa.Column("ideal_cycle_time", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("good_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reject_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("availability", sa.Float(), nullable=False),
        sa.Column("performance", sa.Float(), nullable=False),
        sa.Column("quality", sa.Float(), nullable=False),
        sa.Column("oee", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_oee_tenant_workstation_date", "tenant_id", "workstation_id", "record_date"),
        sa.ForeignKeyConstraint(["workstation_id"], ["workstation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("oee_record")
    op.drop_table("downtime_entry")
    op.drop_table("production_plan_line")
    op.drop_table("production_plan")
    op.drop_table("manufacturing_proposal")
    op.drop_table("routing_operation")
    op.drop_table("routing")
    op.drop_table("workstation_working_hour")
    op.drop_table("workstation")
    op.drop_table("work_order_material_line")
    op.drop_table("work_order")
    op.drop_table("bill_of_materials_item")
    op.drop_table("bill_of_materials")
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS bom_status")
    op.execute("DROP TYPE IF EXISTS work_order_status")
    op.execute("DROP TYPE IF EXISTS wo_transfer_mode")
    op.execute("DROP TYPE IF EXISTS workstation_status")
    op.execute("DROP TYPE IF EXISTS routing_status")
    op.execute("DROP TYPE IF EXISTS manufacturing_proposal_status")
    op.execute("DROP TYPE IF EXISTS production_plan_status")
    op.execute("DROP TYPE IF EXISTS downtime_reason")
