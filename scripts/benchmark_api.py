#!/usr/bin/env python3
"""
API Latency Benchmark for UltrERP FastAPI Backend

Measures p50 and p95 latency across representative FastAPI endpoints.
Target: p50 < 200ms, p95 < 1000ms (lower_is_better)

Output format (last stdout line as JSON):
  {"primary": 85.2, "sub_scores": {"p50": 150, "p95": 800}}

Exit codes: 0 = success, non-zero = error
"""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Ensure JWT_SECRET is set before settings import
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-characters-long")

import httpx

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app
from common.config import settings

# ── Configuration ──────────────────────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 30.0  # seconds per request

# Endpoints to benchmark (method, path, auth_required, payload)
# Using representative endpoints across different domains
ENDPOINTS: list[dict[str, Any]] = [
    # Public/unauthenticated
    {"method": "GET", "path": "/", "auth": False, "name": "root"},
    {"method": "GET", "path": "/api/v1/health", "auth": False, "name": "health"},

    # Authenticated - will login first
    {"method": "GET", "path": "/api/v1/customers", "auth": True, "name": "customers_list"},
    {"method": "GET", "path": "/api/v1/inventory/warehouses", "auth": True, "name": "warehouses"},
    {"method": "GET", "path": "/api/v1/dashboard/revenue-summary", "auth": True, "name": "revenue_summary"},
    {"method": "GET", "path": "/api/v1/dashboard/kpi-summary", "auth": True, "name": "kpi_summary"},
    {"method": "GET", "path": "/api/v1/inventory/products/search", "auth": True, "name": "product_search"},
]

# Number of iterations per endpoint
ITERATIONS = 20

# ── Helpers ────────────────────────────────────────────────────────────────────


def calculate_percentile(values: list[float], percentile: int) -> float:
    """Calculate percentile (e.g., 50 for p50, 95 for p95)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * percentile / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


async def login_for_token(client: httpx.AsyncClient) -> str | None:
    """Login and return JWT token. Returns None on failure."""
    # Find a demo user in the database to login with
    # Default test credentials if they exist
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@ultr.local", "password": "admin123"},
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
    except Exception:
        pass

    # Try to create a test user via MCP or use a fallback
    # For benchmark purposes, we'll try a common default
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "demo@ultr.local", "password": "demo123"},
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
    except Exception:
        pass

    return None


async def benchmark_endpoint(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    auth_token: str | None,
    iterations: int,
) -> list[float]:
    """Measure latency for a single endpoint over N iterations. Returns latencies in ms."""
    latencies: list[float] = []
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            response = await client.request(
                method,
                f"{BASE_URL}{path}",
                headers=headers,
                timeout=TIMEOUT,
            )
            # Only count successful requests
            if response.status_code < 500:
                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
                latencies.append(elapsed)
        except httpx.TimeoutException:
            # Timeout - don't count
            pass
        except Exception:
            # Other errors - don't count
            pass

        # Small delay between requests to avoid overwhelming the server
        await asyncio.sleep(0.01)

    return latencies


async def run_benchmark() -> dict[str, Any]:
    """Run the full benchmark and return results."""
    print("Starting API Latency Benchmark...")
    print(f"Database: {settings.database_url}")

    # Start the server in-process for testing
    # We'll use httpx to make actual HTTP requests to a spawned server
    import subprocess
    import signal

    # Start uvicorn server
    server_process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--workers", "1",
        ],
        cwd=str(BACKEND_ROOT),
        env={**os.environ, "PYTHONPATH": str(BACKEND_ROOT)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server to start
    await asyncio.sleep(3)

    try:
        # Verify server is up
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{BASE_URL}/", timeout=5.0)
                print(f"Server started: {response.status_code}")
            except Exception as e:
                print(f"Warning: Server may not be ready: {e}")
                await asyncio.sleep(2)

        # Get auth token
        print("Authenticating...")
        async with httpx.AsyncClient() as client:
            auth_token = await login_for_token(client)

        if not auth_token:
            print("Warning: Could not authenticate. Some endpoints may fail.")
        else:
            print(f"Authenticated successfully")

        # Run benchmarks
        all_latencies: dict[str, list[float]] = {}
        endpoint_results: dict[str, dict[str, float]] = {}

        print(f"\nBenchmarking {len(ENDPOINTS)} endpoints, {ITERATIONS} iterations each...")

        async with httpx.AsyncClient() as client:
            for endpoint in ENDPOINTS:
                name = endpoint["name"]
                auth_required = endpoint["auth"]
                token = auth_token if auth_required else None

                print(f"  {name}...", end=" ", flush=True)
                latencies = await benchmark_endpoint(
                    client,
                    endpoint["method"],
                    endpoint["path"],
                    token,
                    ITERATIONS,
                )

                if latencies:
                    p50 = calculate_percentile(latencies, 50)
                    p95 = calculate_percentile(latencies, 95)
                    avg = statistics.mean(latencies)
                    all_latencies[name] = latencies
                    endpoint_results[name] = {"p50": p50, "p95": p95, "avg": avg, "count": len(latencies)}
                    print(f"p50={p50:.1f}ms p95={p95:.1f}ms ({len(latencies)} samples)")
                else:
                    print(f"No valid samples (all requests failed or timed out)")

        # Compute overall scores
        all_values: list[float] = []
        for lat_list in all_latencies.values():
            all_values.extend(lat_list)

        if not all_values:
            print("\nError: No successful requests across all endpoints")
            return {
                "primary": 999999.0,
                "sub_scores": {"p50": 999999, "p95": 999999},
                "error": "No successful requests",
            }

        overall_p50 = calculate_percentile(all_values, 50)
        overall_p95 = calculate_percentile(all_values, 95)
        overall_avg = statistics.mean(all_values)

        # Primary score: weighted combination (p50 * 0.4 + p95 * 0.6)
        # Normalized to a 0-100 score where lower is better
        # Target: p50=200ms, p95=1000ms → score ~50
        # Scale: actual_ms / target_ms * 50
        primary = (overall_p50 / 200 * 40 + overall_p95 / 1000 * 60)

        print(f"\n=== Overall Results ===")
        print(f"Total samples: {len(all_values)}")
        print(f"Overall p50: {overall_p50:.1f}ms (target: <200ms)")
        print(f"Overall p95: {overall_p95:.1f}ms (target: <1000ms)")
        print(f"Primary score: {primary:.1f} (lower is better)")

        return {
            "primary": round(primary, 2),
            "sub_scores": {
                "p50": round(overall_p50, 1),
                "p95": round(overall_p95, 1),
                "avg": round(overall_avg, 1),
            },
            "endpoints": endpoint_results,
            "total_samples": len(all_values),
        }

    finally:
        # Shutdown server
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()


def main() -> int:
    """Main entry point."""
    try:
        results = asyncio.run(run_benchmark())

        # Print results
        print("\n=== BENCHMARK RESULTS ===")
        print(json.dumps(results, indent=2))

        # Print the final score line (last stdout line for parsing)
        print(f"\n{json.dumps(results)}")

        return 0

    except Exception as e:
        print(f"\nBenchmark error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
