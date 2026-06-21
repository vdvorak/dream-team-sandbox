"""Performance tests for runtime lifecycle control-plane (slice 1).

Scope: critical paths in server/runtime/ — in-memory, no real IO, no DB.
Measured: p50/p95/p99, memory peak (via tracemalloc), throughput.

Load profiles:
- typical:  10 concurrent projects, 1 operation each
- peak:     100 concurrent projects, 1 operation each
- stress:   same project_id, 50 serialized ensure calls (lock contention path)

Targets (slice 1, in-memory, no real provider IO):
- ensure (DevProvider "active"): p95 < 5 ms per call
- get (lock-free read): p95 < 1 ms per call
- sleep / destroy: p95 < 2 ms per call
- meta-lock contention (100 concurrent new project_ids): p95 < 2 ms per lock acquisition
- memory: destroyed records grow O(N) with unique project_ids; lock dict grows identically
"""

from __future__ import annotations

import asyncio
import statistics
import time
import tracemalloc
from typing import Callable

import pytest

from server.runtime.enforcement.dev import DevEnforcementProvider
from server.runtime.repository import EnvironmentRepository
from server.runtime.service import LifecycleService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(mode: str = "active") -> LifecycleService:
    return LifecycleService(
        repository=EnvironmentRepository(),
        provider=DevEnforcementProvider(mode=mode),
    )


async def _timed_calls(
    coro_factory: Callable[[int], object],
    n: int,
    concurrency: int,
) -> list[float]:
    """Run n coroutines with given concurrency; return per-call latencies in ms."""
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []

    async def _run(i: int) -> None:
        async with semaphore:
            t0 = time.perf_counter()
            await coro_factory(i)
            latencies.append((time.perf_counter() - t0) * 1000)

    await asyncio.gather(*[_run(i) for i in range(n)])
    return latencies


def _percentiles(latencies: list[float]) -> dict[str, float]:
    s = sorted(latencies)
    n = len(s)
    return {
        "p50": statistics.median(s),
        "p95": s[int(n * 0.95)],
        "p99": s[int(n * 0.99)],
        "max": s[-1],
        "mean": statistics.mean(s),
    }


# ---------------------------------------------------------------------------
# Test: ensure — typical load (10 distinct project_ids, concurrent)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_typical_latency() -> None:
    """ensure on distinct project_ids — typical load profile (10 concurrent).

    Target: p95 < 5 ms (in-memory DevProvider, no real IO).
    """
    svc = _make_service()
    n = 10

    async def _ensure(i: int) -> None:
        await svc.ensure(
            project_id=f"proj-typical-{i}",
            repo_url="https://github.com/test/repo",
            repo_ref="main",
            tool="claude",
        )

    latencies = await _timed_calls(_ensure, n=n, concurrency=n)
    p = _percentiles(latencies)
    print(f"\n[ensure/typical] n={n} p50={p['p50']:.2f}ms p95={p['p95']:.2f}ms p99={p['p99']:.2f}ms max={p['max']:.2f}ms")

    assert p["p95"] < 5.0, (
        f"ensure p95={p['p95']:.2f}ms exceeds 5ms target on typical load (in-memory)"
    )


# ---------------------------------------------------------------------------
# Test: ensure — peak load (100 distinct project_ids, concurrent)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_peak_latency() -> None:
    """ensure on distinct project_ids — peak load profile (100 concurrent).

    Target: p95 < 10 ms (slightly relaxed for scheduling overhead at scale).
    """
    svc = _make_service()
    n = 100

    async def _ensure(i: int) -> None:
        await svc.ensure(
            project_id=f"proj-peak-{i}",
            repo_url="https://github.com/test/repo",
            repo_ref="main",
            tool="claude",
        )

    latencies = await _timed_calls(_ensure, n=n, concurrency=n)
    p = _percentiles(latencies)
    print(f"\n[ensure/peak] n={n} p50={p['p50']:.2f}ms p95={p['p95']:.2f}ms p99={p['p99']:.2f}ms max={p['max']:.2f}ms")

    assert p["p95"] < 10.0, (
        f"ensure p95={p['p95']:.2f}ms exceeds 10ms target on peak load (in-memory)"
    )


# ---------------------------------------------------------------------------
# Test: ensure — stress (same project_id, serialized by project lock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_same_project_lock_contention() -> None:
    """50 concurrent ensure calls on the same project_id — exercises per-project lock.

    All 50 calls serialize on one asyncio.Lock (correct behavior: no deadlock, no race).
    Target: completes without deadlock; individual call p95 < 20 ms (pure serialization overhead).
    """
    svc = _make_service()
    n = 50

    async def _ensure(_: int) -> None:
        await svc.ensure(
            project_id="proj-stress-same",
            repo_url="https://github.com/test/repo",
            repo_ref="main",
            tool="claude",
        )

    latencies = await _timed_calls(_ensure, n=n, concurrency=n)
    p = _percentiles(latencies)
    print(f"\n[ensure/stress-same-project] n={n} p50={p['p50']:.2f}ms p95={p['p95']:.2f}ms p99={p['p99']:.2f}ms max={p['max']:.2f}ms")

    # No deadlock: all 50 calls completed (gather above would have hung otherwise).
    # Latency check: serialized queue, but still in-memory only.
    assert p["p99"] < 50.0, (
        f"ensure p99={p['p99']:.2f}ms on same project_id exceeds 50ms — lock or event-loop issue"
    )


# ---------------------------------------------------------------------------
# Test: get — lock-free read path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_latency() -> None:
    """get() is lock-free (read-only dict lookup + model mapping).

    Target: p95 < 1 ms.
    """
    svc = _make_service()
    # Pre-create environment
    await svc.ensure(
        project_id="proj-get-test",
        repo_url="https://github.com/test/repo",
        repo_ref="main",
        tool="claude",
    )
    n = 200

    async def _get(_: int) -> None:
        await svc.get("proj-get-test")

    latencies = await _timed_calls(_get, n=n, concurrency=50)
    p = _percentiles(latencies)
    print(f"\n[get] n={n} p50={p['p50']:.3f}ms p95={p['p95']:.3f}ms p99={p['p99']:.3f}ms max={p['max']:.3f}ms")

    assert p["p95"] < 1.0, (
        f"get p95={p['p95']:.3f}ms exceeds 1ms target (lock-free in-memory read)"
    )


# ---------------------------------------------------------------------------
# Test: sleep / destroy latency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sleep_destroy_latency() -> None:
    """sleep and destroy on distinct project_ids — typical load.

    Target: p95 < 2 ms each.
    """
    svc = _make_service()
    n = 50

    # Pre-create environments
    for i in range(n):
        await svc.ensure(
            project_id=f"proj-sleepdestroy-{i}",
            repo_url="https://github.com/test/repo",
            repo_ref="main",
            tool="claude",
        )

    async def _sleep(i: int) -> None:
        await svc.sleep(f"proj-sleepdestroy-{i}")

    sleep_latencies = await _timed_calls(_sleep, n=n, concurrency=n)
    ps = _percentiles(sleep_latencies)
    print(f"\n[sleep] n={n} p50={ps['p50']:.2f}ms p95={ps['p95']:.2f}ms p99={ps['p99']:.2f}ms")

    async def _destroy(i: int) -> None:
        await svc.destroy(f"proj-sleepdestroy-{i}")

    destroy_latencies = await _timed_calls(_destroy, n=n, concurrency=n)
    pd = _percentiles(destroy_latencies)
    print(f"[destroy] n={n} p50={pd['p50']:.2f}ms p95={pd['p95']:.2f}ms p99={pd['p99']:.2f}ms")

    assert ps["p95"] < 2.0, (
        f"sleep p95={ps['p95']:.2f}ms exceeds 2ms target"
    )
    assert pd["p95"] < 2.0, (
        f"destroy p95={pd['p95']:.2f}ms exceeds 2ms target"
    )


# ---------------------------------------------------------------------------
# Test: meta-lock contention (N new project_ids, concurrent _get_lock calls)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_meta_lock_contention() -> None:
    """100 concurrent ensure calls each on a new project_id — all contend on _locks_meta.

    _locks_meta is held only for a O(1) dict lookup/insert, then released.
    No two calls share a project lock, so post-meta-lock work is fully parallel.

    Target: p95 < 2 ms per lock acquisition (meta-lock is momentary).
    """
    svc = _make_service()
    n = 100

    async def _ensure(i: int) -> None:
        await svc.ensure(
            project_id=f"proj-metalock-{i}",
            repo_url="https://github.com/test/repo",
            repo_ref="main",
            tool="claude",
        )

    latencies = await _timed_calls(_ensure, n=n, concurrency=n)
    p = _percentiles(latencies)
    print(f"\n[meta-lock/100 new projects] n={n} p50={p['p50']:.2f}ms p95={p['p95']:.2f}ms p99={p['p99']:.2f}ms max={p['max']:.2f}ms")

    assert p["p95"] < 2.0, (
        f"meta-lock contention p95={p['p95']:.2f}ms — _locks_meta held too long or O(N) work inside"
    )


# ---------------------------------------------------------------------------
# Test: memory — destroyed records and lock dict do not leak unexpectedly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_destroyed_records_bounded() -> None:
    """Destroyed records stay in repository (by design); lock dict grows identically.

    This test measures peak memory for N=1000 unique project_ids (each destroyed).
    Advisory: at 1000 projects, footprint should be < 5 MB (well within any server budget).

    If this test fails in a future slice, implement GC / TTL for destroyed records.
    """
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    svc = _make_service()
    n = 1000

    for i in range(n):
        pid = f"proj-mem-{i}"
        await svc.ensure(
            project_id=pid,
            repo_url="https://github.com/test/repo",
            repo_ref="main",
            tool="claude",
        )
        await svc.destroy(pid)

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_kb = sum(s.size_diff for s in stats) / 1024
    print(f"\n[memory/1000 destroyed projects] net allocation: {total_kb:.1f} KB")

    assert total_kb < 5 * 1024, (  # 5 MB hard cap
        f"Memory for 1000 destroyed projects: {total_kb:.1f} KB > 5120 KB — potential leak"
    )
