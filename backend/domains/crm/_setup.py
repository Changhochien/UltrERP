"""CRM settings and master-data services."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.errors import ValidationError
from common.tenant import DEFAULT_TENANT_ID, set_tenant
from domains.crm._shared import _trim
from domains.crm.models import CRMCustomerGroup, CRMSalesStage, CRMSettings, CRMTerritory
from domains.crm.schemas import (
    CRMCustomerGroupCreate,
    CRMCustomerGroupResponse,
    CRMCustomerGroupUpdate,
    CRMDuplicatePolicy,
    CRMSalesStageCreate,
    CRMSalesStageResponse,
    CRMSalesStageUpdate,
    CRMSettingsResponse,
    CRMSettingsUpdate,
    CRMSetupBundleResponse,
    CRMTerritoryCreate,
    CRMTerritoryResponse,
    CRMTerritoryUpdate,
)

DEFAULT_CRM_SETTINGS = CRMSettingsResponse()
DEFAULT_CRM_SALES_STAGES: tuple[tuple[str, int, int], ...] = (
    ("qualification", 10, 10),
    ("proposal", 50, 20),
    ("negotiation", 75, 30),
    ("commitment", 90, 40),
)
DEFAULT_CRM_TERRITORIES: tuple[tuple[str, int], ...] = (
    ("North", 10),
    ("Taipei", 20),
    ("Central", 30),
    ("South", 40),
)
DEFAULT_CRM_CUSTOMER_GROUPS: tuple[tuple[str, int], ...] = (
    ("Industrial", 10),
    ("Dealer", 20),
    ("End User", 30),
)
def _extract_settings_fields(record: object) -> dict[str, object]:
    """Extract CRM settings fields from a record, using defaults for missing fields."""
    defaults = DEFAULT_CRM_SETTINGS.model_dump()
    return {
        "lead_duplicate_policy": CRMDuplicatePolicy(
            getattr(record, "lead_duplicate_policy", defaults["lead_duplicate_policy"])
        ),
        "contact_creation_enabled": bool(
            getattr(record, "contact_creation_enabled", defaults["contact_creation_enabled"])
        ),
        "default_quotation_validity_days": int(
            getattr(record, "default_quotation_validity_days", defaults["default_quotation_validity_days"])
        ),
        "carry_forward_communications": bool(
            getattr(record, "carry_forward_communications", defaults["carry_forward_communications"])
        ),
        "carry_forward_comments": bool(
            getattr(record, "carry_forward_comments", defaults["carry_forward_comments"])
        ),
        "opportunity_auto_close_days": getattr(
            record, "opportunity_auto_close_days", defaults["opportunity_auto_close_days"]
        ),
    }


def _serialize_crm_settings(record: CRMSettings | None) -> CRMSettingsResponse:
    if record is None:
        return CRMSettingsResponse()
    return CRMSettingsResponse(**_extract_settings_fields(record))


async def get_crm_settings(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> CRMSettingsResponse:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMSettings).where(CRMSettings.tenant_id == tid)
        )
        return _serialize_crm_settings(result.scalar_one_or_none())


async def update_crm_settings(
    session: AsyncSession,
    data: CRMSettingsUpdate,
    tenant_id: uuid.UUID | None = None,
) -> CRMSettingsResponse:
    tid = tenant_id or DEFAULT_TENANT_ID

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMSettings).where(CRMSettings.tenant_id == tid)
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = CRMSettings(tenant_id=tid)
            session.add(record)

        # Apply non-None updates from data to record
        for field_name in data.model_fields_set:
            new_value = getattr(data, field_name)
            if new_value is not None:
                setattr(record, field_name, new_value)
        record.updated_at = datetime.now(tz=UTC)

    return _serialize_crm_settings(record)


async def _resolve_effective_quotation_valid_till(
    session: AsyncSession,
    transaction_date: date,
    valid_till: date | None,
    tenant_id: uuid.UUID,
) -> date:
    if valid_till is not None:
        return valid_till

    settings = await get_crm_settings(session, tenant_id=tenant_id)
    return transaction_date + timedelta(days=settings.default_quotation_validity_days)


def _default_sales_stage_names() -> set[str]:
    return {name for name, _, _ in DEFAULT_CRM_SALES_STAGES}


def _default_territory_names() -> set[str]:
    return {name for name, _ in DEFAULT_CRM_TERRITORIES}


def _default_customer_group_names() -> set[str]:
    return {name for name, _ in DEFAULT_CRM_CUSTOMER_GROUPS}


def _serialize_sales_stage(record: CRMSalesStage) -> CRMSalesStageResponse:
    return CRMSalesStageResponse.model_validate(record)


def _serialize_territory(record: CRMTerritory) -> CRMTerritoryResponse:
    return CRMTerritoryResponse.model_validate(record)


def _serialize_customer_group(record: CRMCustomerGroup) -> CRMCustomerGroupResponse:
    return CRMCustomerGroupResponse.model_validate(record)


async def _lookup_active_master_name(
    session: AsyncSession,
    model: type[CRMSalesStage] | type[CRMTerritory] | type[CRMCustomerGroup],
    name: str,
    tenant_id: uuid.UUID,
) -> object | None:
    async with session.begin():
        await set_tenant(session, tenant_id)
        result = await session.execute(
            select(model).where(
                model.tenant_id == tenant_id,
                model.name == name,
                model.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()


async def _ensure_sales_stage_supported(
    session: AsyncSession,
    sales_stage: str,
    tenant_id: uuid.UUID,
) -> str:
    normalized = _trim(sales_stage) or "qualification"
    if normalized in _default_sales_stage_names():
        return normalized
    record = await _lookup_active_master_name(session, CRMSalesStage, normalized, tenant_id)
    if record is None:
        raise ValidationError(
            [{"field": "sales_stage", "message": "Select a configured sales stage."}]
        )
    return normalized


async def _ensure_territory_supported(
    session: AsyncSession,
    territory: str,
    tenant_id: uuid.UUID,
) -> str:
    normalized = _trim(territory)
    if not normalized or normalized in _default_territory_names():
        return normalized
    record = await _lookup_active_master_name(session, CRMTerritory, normalized, tenant_id)
    if record is None:
        raise ValidationError(
            [{"field": "territory", "message": "Select a configured territory."}]
        )
    return normalized


async def _ensure_customer_group_supported(
    session: AsyncSession,
    customer_group: str,
    tenant_id: uuid.UUID,
) -> str:
    normalized = _trim(customer_group)
    if not normalized or normalized in _default_customer_group_names():
        return normalized
    record = await _lookup_active_master_name(
        session,
        CRMCustomerGroup,
        normalized,
        tenant_id,
    )
    if record is None:
        raise ValidationError(
            [
                {
                    "field": "customer_group",
                    "message": "Select a configured customer group.",
                }
            ]
        )
    return normalized


async def list_sales_stages(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> list[CRMSalesStage]:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMSalesStage)
            .where(CRMSalesStage.tenant_id == tid)
            .order_by(CRMSalesStage.sort_order.asc(), CRMSalesStage.name.asc())
        )
        items = list(result.scalars().all())
        if items:
            return items

        defaults = [
            CRMSalesStage(
                id=uuid.uuid4(),
                tenant_id=tid,
                name=name,
                probability=probability,
                sort_order=sort_order,
                is_active=True,
            )
            for name, probability, sort_order in DEFAULT_CRM_SALES_STAGES
        ]
        for item in defaults:
            session.add(item)
        return defaults


async def list_territories(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> list[CRMTerritory]:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMTerritory)
            .where(CRMTerritory.tenant_id == tid)
            .order_by(CRMTerritory.sort_order.asc(), CRMTerritory.name.asc())
        )
        items = list(result.scalars().all())
        if items:
            return items

        defaults = [
            CRMTerritory(
                id=uuid.uuid4(),
                tenant_id=tid,
                name=name,
                parent_id=None,
                is_group=False,
                sort_order=sort_order,
                is_active=True,
            )
            for name, sort_order in DEFAULT_CRM_TERRITORIES
        ]
        for item in defaults:
            session.add(item)
        return defaults


async def list_customer_groups(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> list[CRMCustomerGroup]:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMCustomerGroup)
            .where(CRMCustomerGroup.tenant_id == tid)
            .order_by(CRMCustomerGroup.sort_order.asc(), CRMCustomerGroup.name.asc())
        )
        items = list(result.scalars().all())
        if items:
            return items

        defaults = [
            CRMCustomerGroup(
                id=uuid.uuid4(),
                tenant_id=tid,
                name=name,
                parent_id=None,
                is_group=False,
                sort_order=sort_order,
                is_active=True,
            )
            for name, sort_order in DEFAULT_CRM_CUSTOMER_GROUPS
        ]
        for item in defaults:
            session.add(item)
        return defaults


async def get_crm_setup_bundle(
    session: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> CRMSetupBundleResponse:
    tid = tenant_id or DEFAULT_TENANT_ID
    settings = await get_crm_settings(session, tenant_id=tid)
    sales_stages = await list_sales_stages(session, tenant_id=tid)
    territories = await list_territories(session, tenant_id=tid)
    customer_groups = await list_customer_groups(session, tenant_id=tid)
    return CRMSetupBundleResponse(
        settings=settings,
        sales_stages=[_serialize_sales_stage(item) for item in sales_stages],
        territories=[_serialize_territory(item) for item in territories],
        customer_groups=[_serialize_customer_group(item) for item in customer_groups],
    )


async def create_sales_stage(
    session: AsyncSession,
    data: CRMSalesStageCreate,
    tenant_id: uuid.UUID | None = None,
) -> CRMSalesStage:
    tid = tenant_id or DEFAULT_TENANT_ID
    name = _trim(data.name)
    if not name:
        raise ValidationError(
            [{"field": "name", "message": "Sales stage name is required."}]
        )

    await list_sales_stages(session, tenant_id=tid)
    async with session.begin():
        await set_tenant(session, tid)
        existing = await session.execute(
            select(CRMSalesStage).where(
                CRMSalesStage.tenant_id == tid,
                CRMSalesStage.name == name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(
                [{"field": "name", "message": "Sales stage already exists."}]
            )

        stage = CRMSalesStage(
            tenant_id=tid,
            name=name,
            probability=data.probability,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
        session.add(stage)
        return stage


async def update_sales_stage(
    session: AsyncSession,
    stage_id: uuid.UUID,
    data: CRMSalesStageUpdate,
    tenant_id: uuid.UUID | None = None,
) -> CRMSalesStage | None:
    tid = tenant_id or DEFAULT_TENANT_ID
    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMSalesStage).where(
                CRMSalesStage.id == stage_id,
                CRMSalesStage.tenant_id == tid,
            )
        )
        stage = result.scalar_one_or_none()
        if stage is None:
            return None

        if data.name is not None:
            name = _trim(data.name)
            duplicate = await session.execute(
                select(CRMSalesStage).where(
                    CRMSalesStage.tenant_id == tid,
                    CRMSalesStage.name == name,
                    CRMSalesStage.id != stage_id,
                )
            )
            if duplicate.scalar_one_or_none() is not None:
                raise ValidationError(
                    [{"field": "name", "message": "Sales stage already exists."}]
                )
            stage.name = name
        if data.probability is not None:
            stage.probability = data.probability
        if data.sort_order is not None:
            stage.sort_order = data.sort_order
        if data.is_active is not None:
            stage.is_active = data.is_active
        stage.updated_at = datetime.now(tz=UTC)
        return stage


async def _validate_tree_parent(
    session: AsyncSession,
    model: type[CRMTerritory] | type[CRMCustomerGroup],
    parent_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
    current_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    if parent_id is None:
        return None
    if current_id is not None and parent_id == current_id:
        raise ValidationError(
            [
                {
                    "field": "parent_id",
                    "message": "A master record cannot be its own parent.",
                }
            ]
        )

    async with session.begin():
        await set_tenant(session, tenant_id)
        result = await session.execute(
            select(model).where(
                model.id == parent_id,
                model.tenant_id == tenant_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValidationError(
                [{"field": "parent_id", "message": "Parent master record not found."}]
            )
    return parent_id


async def create_territory(
    session: AsyncSession,
    data: CRMTerritoryCreate,
    tenant_id: uuid.UUID | None = None,
) -> CRMTerritory:
    tid = tenant_id or DEFAULT_TENANT_ID
    name = _trim(data.name)
    if not name:
        raise ValidationError(
            [{"field": "name", "message": "Territory name is required."}]
        )

    await list_territories(session, tenant_id=tid)
    parent_id = await _validate_tree_parent(session, CRMTerritory, data.parent_id, tid)
    async with session.begin():
        await set_tenant(session, tid)
        existing = await session.execute(
            select(CRMTerritory).where(
                CRMTerritory.tenant_id == tid,
                CRMTerritory.name == name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(
                [{"field": "name", "message": "Territory already exists."}]
            )

        territory = CRMTerritory(
            tenant_id=tid,
            name=name,
            parent_id=parent_id,
            is_group=data.is_group,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
        session.add(territory)
        return territory


async def update_territory(
    session: AsyncSession,
    territory_id: uuid.UUID,
    data: CRMTerritoryUpdate,
    tenant_id: uuid.UUID | None = None,
) -> CRMTerritory | None:
    tid = tenant_id or DEFAULT_TENANT_ID

    # Validate parent exists before starting the update transaction
    parent_id = await _validate_tree_parent(
        session,
        CRMTerritory,
        data.parent_id,
        tid,
        current_id=territory_id,
    )

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMTerritory).where(
                CRMTerritory.id == territory_id,
                CRMTerritory.tenant_id == tid,
            )
        )
        territory = result.scalar_one_or_none()
        if territory is None:
            return None

        if data.name is not None:
            name = _trim(data.name)
            duplicate = await session.execute(
                select(CRMTerritory).where(
                    CRMTerritory.tenant_id == tid,
                    CRMTerritory.name == name,
                    CRMTerritory.id != territory_id,
                )
            )
            if duplicate.scalar_one_or_none() is not None:
                raise ValidationError(
                    [{"field": "name", "message": "Territory already exists."}]
                )
            territory.name = name
        if "parent_id" in data.model_fields_set:
            territory.parent_id = parent_id
        if data.is_group is not None:
            territory.is_group = data.is_group
        if data.sort_order is not None:
            territory.sort_order = data.sort_order
        if data.is_active is not None:
            territory.is_active = data.is_active
        territory.updated_at = datetime.now(tz=UTC)
        return territory


async def create_customer_group(
    session: AsyncSession,
    data: CRMCustomerGroupCreate,
    tenant_id: uuid.UUID | None = None,
) -> CRMCustomerGroup:
    tid = tenant_id or DEFAULT_TENANT_ID
    name = _trim(data.name)
    if not name:
        raise ValidationError(
            [{"field": "name", "message": "Customer group name is required."}]
        )

    await list_customer_groups(session, tenant_id=tid)
    parent_id = await _validate_tree_parent(
        session,
        CRMCustomerGroup,
        data.parent_id,
        tid,
    )
    async with session.begin():
        await set_tenant(session, tid)
        existing = await session.execute(
            select(CRMCustomerGroup).where(
                CRMCustomerGroup.tenant_id == tid,
                CRMCustomerGroup.name == name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValidationError(
                [{"field": "name", "message": "Customer group already exists."}]
            )

        customer_group = CRMCustomerGroup(
            tenant_id=tid,
            name=name,
            parent_id=parent_id,
            is_group=data.is_group,
            sort_order=data.sort_order,
            is_active=data.is_active,
        )
        session.add(customer_group)
        return customer_group


async def update_customer_group(
    session: AsyncSession,
    customer_group_id: uuid.UUID,
    data: CRMCustomerGroupUpdate,
    tenant_id: uuid.UUID | None = None,
) -> CRMCustomerGroup | None:
    tid = tenant_id or DEFAULT_TENANT_ID

    # Validate parent exists before starting the update transaction
    parent_id = await _validate_tree_parent(
        session,
        CRMCustomerGroup,
        data.parent_id,
        tid,
        current_id=customer_group_id,
    )

    async with session.begin():
        await set_tenant(session, tid)
        result = await session.execute(
            select(CRMCustomerGroup).where(
                CRMCustomerGroup.id == customer_group_id,
                CRMCustomerGroup.tenant_id == tid,
            )
        )
        customer_group = result.scalar_one_or_none()
        if customer_group is None:
            return None

        if data.name is not None:
            name = _trim(data.name)
            duplicate = await session.execute(
                select(CRMCustomerGroup).where(
                    CRMCustomerGroup.tenant_id == tid,
                    CRMCustomerGroup.name == name,
                    CRMCustomerGroup.id != customer_group_id,
                )
            )
            if duplicate.scalar_one_or_none() is not None:
                raise ValidationError(
                    [{"field": "name", "message": "Customer group already exists."}]
                )
            customer_group.name = name
        if "parent_id" in data.model_fields_set:
            customer_group.parent_id = parent_id
        if data.is_group is not None:
            customer_group.is_group = data.is_group
        if data.sort_order is not None:
            customer_group.sort_order = data.sort_order
        if data.is_active is not None:
            customer_group.is_active = data.is_active
        customer_group.updated_at = datetime.now(tz=UTC)
        return customer_group
