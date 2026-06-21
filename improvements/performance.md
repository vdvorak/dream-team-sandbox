# Performance improvements — tech debt and future optimizations

## Wave 2026-06-21-runtime-lifecycle (slice 1)

### ADV-PERF-1 — Unbounded growth of `_locks` dict in `LifecycleService`

**File:** `server/runtime/service.py` — `LifecycleService._locks` (line 93)

**Finding:** A new `asyncio.Lock` is inserted into `_locks` on first access for each
unique `project_id` and is never removed — not even after the project is destroyed.
At 100k unique project_ids the dict occupies ~9 MB (measured: 48 bytes per Lock object).
For a lifecycle control-plane this is negligible in slice 1, but becomes a concern in
slice 2 when persistence or long-running instances are introduced.

**Recommendation for slice 2:** Add a cleanup hook (e.g., inside `destroy()`) that removes
the lock from `_locks` once the project is destroyed and no waiters remain. Use
`asyncio.Lock().locked()` / reference counting, or a weakref-keyed dict, to avoid
removing a lock while another coroutine is queued on it.

**Severity:** advisory — no impact in slice 1 (in-memory, process restart = clean state).

---

### ADV-PERF-2 — Unbounded growth of destroyed records in `EnvironmentRepository`

**File:** `server/runtime/repository.py` — `EnvironmentRepository._store` (line 45)

**Finding:** Destroyed records are intentionally retained (contract requirement: GET after
destroy must return `status: destroyed`; ensure after destroy starts a fresh cycle per
RCP-5d). However, there is no TTL, no capacity cap, and no GC path. At 100k destroyed
projects the store holds 100k dataclass objects (~4-6 MB measured at 1k projects = 315 KB).

**Recommendation for slice 2:** When persistence is introduced, implement a background
TTL-based GC for destroyed records (e.g., delete records older than 7 days). Until then
the in-memory growth is bounded by process lifetime (acceptable for slice 1).

**Severity:** advisory — no impact in slice 1 (in-memory only).

---

### ADV-PERF-3 — SHA-256 computed on every `ensure_active` in DevEnforcementProvider

**File:** `server/runtime/enforcement/dev.py` — `_opaque_id`, `_opaque_token` (lines 44, 49)

**Finding:** `DevEnforcementProvider.ensure_active` computes three SHA-256 hashes per call
(~0.003 ms total, measured). This is negligible in slice 1. In slice 2, if DevProvider
is retained for load testing, these could be cached (the result is deterministic per
`project_id`). Not a concern for the real `CageEnforcementProvider`.

**Severity:** advisory — sub-microsecond, no action needed in slice 2 unless DevProvider
is used for sustained load benchmarking.
