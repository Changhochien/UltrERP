#!/usr/bin/env python3
"""Functional test suite for UltrERP MCP Server PoC."""

import asyncio
import json
from fastmcp import Client
from fastmcp.client import StreamableHttpTransport

ADMIN = {"X-API-Key": "sk-erp-admin"}
READONLY = {"X-API-Key": "sk-erp-readonly"}
SALES = {"X-API-Key": "sk-erp-sales"}
FINANCE = {"X-API-Key": "sk-erp-finance"}


async def main():
    all_passed = True

    # ------------------------------------------------------------------
    # 1. customers.list returns mock customer data
    # ------------------------------------------------------------------
    print("=== 1. customers.list returns mock customer data ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=ADMIN)) as c:
            r = await c.call_tool("customers_list", {})
            data = json.loads(r.content[0].text)
            assert data["total"] == 5, f"Expected 5 customers, got {data['total']}"
            assert data["customers"][0]["tax_id"] == "12345678"
            print(f"  PASS: got {data['total']} customers, first has valid MOD11 tax_id")
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 2. customers.create validates tax_id with MOD11 (valid)
    # ------------------------------------------------------------------
    print("\n=== 2. customers.create validates MOD11 (valid) ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=ADMIN)) as c:
            r = await c.call_tool("customers_create", {
                "name": "New Test Corp",
                "tax_id": "11111116",  # MOD11-valid: base 1111111, check 6
                "email": "newtest@example.com",
            })
            data = json.loads(r.content[0].text)
            assert data["id"].startswith("c_")
            print(f"  PASS: created customer id={data['id']}")
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 3. customers.create rejects invalid MOD11
    # ------------------------------------------------------------------
    print("\n=== 3. customers.create rejects invalid MOD11 tax_id ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=ADMIN)) as c:
            try:
                r = await c.call_tool("customers_create", {
                    "name": "Bad Tax Co",
                    "tax_id": "10101010",  # invalid check digit
                    "email": "bad@example.com",
                })
                print("  FAIL: should have raised ToolError")
                all_passed = False
            except Exception as e:
                assert "MOD11" in str(e) or "VALIDATION_ERROR" in str(e)
                print(f"  PASS: raised ValidationError: {str(e)[:80]}")
    except Exception as e:
        print(f"  FAIL (outer): {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 4. invoices.create calculates 5% tax correctly
    # ------------------------------------------------------------------
    print("\n=== 4. invoices.create calculates 5% tax ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=ADMIN)) as c:
            r = await c.call_tool("invoices_create", {
                "customer_id": "c_001",
                "due_date": "2026-04-30",
                "line_items": [
                    {"description": "Widgets", "quantity": 10, "unit_price": 100.0, "tax_rate": 0.05},
                    {"description": "Setup",   "quantity":  1, "unit_price":  50.0, "tax_rate": 0.05},
                ],
            })
            data = json.loads(r.content[0].text)
            # subtotal = 10*100 + 1*50 = 1050
            # tax = 1050 * 0.05 = 52.5
            # total = 1102.5
            assert data["subtotal"] == 1050.0, f"subtotal={data['subtotal']}"
            assert data["total_tax"] == 52.5, f"tax={data['total_tax']}"
            assert data["total"] == 1102.5, f"total={data['total']}"
            print(f"  PASS: subtotal={data['subtotal']}, tax={data['total_tax']}, total={data['total']}")
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 5. invoices.list with status filter
    # ------------------------------------------------------------------
    print("\n=== 5. invoices.list with status filter ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=ADMIN)) as c:
            r = await c.call_tool("invoices_list", {"status": "open"})
            data = json.loads(r.content[0].text)
            assert data["total"] == 1 and data["invoices"][0]["status"] == "open"
            print(f"  PASS: {data['total']} open invoice(s)")
    except Exception as e:
        print(f"  FAIL: {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 6. Unauthorized: READONLY key → 403 on invoices.create
    # ------------------------------------------------------------------
    print("\n=== 6. READONLY key → 403 on invoices.create ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=READONLY)) as c:
            try:
                r = await c.call_tool("invoices_create", {
                    "customer_id": "c_001", "due_date": "2026-04-30",
                    "line_items": [{"description": "X", "quantity": 1, "unit_price": 10.0}],
                })
                print("  FAIL: should have raised error")
                all_passed = False
            except Exception as e:
                assert "scope" in str(e).lower() or "PERMISSION" in str(e) or "invoices:write" in str(e)
                print(f"  PASS: got scope error: {str(e)[:100]}")
    except Exception as e:
        print(f"  FAIL (outer): {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 7. Unauthorized: no API key → 401
    # ------------------------------------------------------------------
    print("\n=== 7. No API key → 401 ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers={})) as c:
            try:
                r = await c.call_tool("customers_list", {})
                print("  FAIL: should have raised error")
                all_passed = False
            except Exception as e:
                assert "X-API-Key" in str(e) or "401" in str(e) or "API key" in str(e)
                print(f"  PASS: got auth error: {str(e)[:100]}")
    except Exception as e:
        print(f"  FAIL (outer): {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 8. Unauthorized: SALES key → 403 on invoices.create
    # ------------------------------------------------------------------
    print("\n=== 8. SALES key → 403 on invoices.create ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=SALES)) as c:
            try:
                r = await c.call_tool("invoices_create", {
                    "customer_id": "c_001", "due_date": "2026-04-30",
                    "line_items": [{"description": "X", "quantity": 1, "unit_price": 10.0}],
                })
                print("  FAIL: should have raised error")
                all_passed = False
            except Exception as e:
                print(f"  PASS: got scope error: {str(e)[:100]}")
    except Exception as e:
        print(f"  FAIL (outer): {e}")
        all_passed = False

    # ------------------------------------------------------------------
    # 9. NotFoundError for invalid customer_id
    # ------------------------------------------------------------------
    print("\n=== 9. invoices.create with invalid customer_id ===")
    try:
        async with Client(StreamableHttpTransport(url="http://localhost:8000/mcp", headers=ADMIN)) as c:
            try:
                r = await c.call_tool("invoices_create", {
                    "customer_id": "c_999", "due_date": "2026-04-30",
                    "line_items": [{"description": "X", "quantity": 1, "unit_price": 10.0}],
                })
                print("  FAIL: should have raised NotFoundError")
                all_passed = False
            except Exception as e:
                assert "NOT_FOUND" in str(e) or "not found" in str(e)
                print(f"  PASS: got NotFoundError: {str(e)[:100]}")
    except Exception as e:
        print(f"  FAIL (outer): {e}")
        all_passed = False

    # ------------------------------------------------------------------
    print()
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")


if __name__ == "__main__":
    asyncio.run(main())
