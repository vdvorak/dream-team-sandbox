#!/usr/bin/env python3
"""Acceptance naostro: incremental-reflow scoped re-flow na REÁLNÉM grafu (delivery.yaml).

Scénář = E2E `createdat` (backend-only feature "get-user vrací created_at"):
  intake→product→feasibility→architecture→db-schema→backend→qa→fan-out(performance,spec-audit,security,code-quality)
Audit-vrstva: code-quality advisory (UserView dup, BEZ re-flow), spec-audit BLOCKING
(spec open-question vs contract CLOSED) → re-flow zpět na product.

product opraví JEN doc-sekci spec (`changed:[spec]`); architecture re-runne, ale contract
se nezmění (`changed:none`). Acceptance: re-flow zasáhne JEN spec-konzumenty
{product, feasibility, architecture, db-schema, spec-audit}, a NE backend/qa/performance/security/code-quality
(kód + jeho auditoři zůstanou hotové). Tím se ověří E1-depth fix na reálném grafu.

Drivuje přes reálné scripts/pipeline/{run,result}.sh (ne syntetický seed).
Spuštění:  python3 accept-createdat.py     (repo root odvozen z umístění skriptu;
           override přes DT_REPO=/cesta/k/dream-team). Exit 0 = acceptance prošla.
"""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("DT_REPO") or os.path.abspath(os.path.join(HERE, "..", ".."))
PIPE = os.path.join(REPO, "scripts", "pipeline")
GRAPH = os.path.join(REPO, "pipeline", "delivery.yaml")
RUN = "createdat-accept"

WORK = tempfile.mkdtemp(prefix="createdat-accept-")
ENV = dict(os.environ, PIPELINE_GRAPH=GRAPH)

# backend-only projekt: server+db, žádné UI, žádný deploy; active_targets deklarovaně
# prázdné → T1 gating vyfiltruje web/mobile/desktop (klienti off).
with open(os.path.join(WORK, "project-config.md"), "w") as fh:
    fh.write("# project-config\n\n```yaml\n"
             "flags:\n  has_server: true\n  has_db: true\n  has_ui: false\n  has_deploy: false\n"
             "active_targets: {}\n```\n")

def sh(*args):
    return subprocess.run(["bash", os.path.join(PIPE, args[0]+".sh"), *args[1:]],
                          cwd=WORK, env=ENV, capture_output=True, text=True)

def drive():
    return subprocess.run(["bash", os.path.join(PIPE, "run.sh"), "drive"],
                          cwd=WORK, env=ENV, capture_output=True, text=True)

def state():
    import yaml
    m = re.search(r"```yaml\s*\n(.*?)\n```",
                  open(os.path.join(WORK, "current-run.md")).read(), re.S)
    return yaml.safe_load(m.group(1))

def done(node, outcome="PASS", changed="__default__", **extra):
    import yaml
    env = {"run": RUN, "node": node, "outcome": outcome,
           "time": {"started": "2026-06-12T10:00:00", "ended": "2026-06-12T10:00:01"}}
    if changed != "__default__":
        env["changed"] = changed
    env.update(extra)
    p = os.path.join(WORK, "env.yaml")
    open(p, "w").write(yaml.safe_dump(env, sort_keys=False, allow_unicode=True))
    r = sh("result", "env.yaml")
    if r.returncode != 0:
        print(f"  !! result.sh FAIL pro {node}:\n{r.stdout}{r.stderr}"); sys.exit(1)

# seed
r = sh("run", "start", RUN)
if r.returncode != 0:
    print("seed FAIL:", r.stdout, r.stderr); sys.exit(1)

# completion plan: (node, visit) -> kwargs pro done()
visits = {}
def plan(node):
    v = visits.get(node, 0) + 1
    visits[node] = v
    if node == "intake":                       # router → klasifikace
        return dict(outcome="PASS", class_="feature")
    if node == "product":                        # 1. = plný; re-run = jen spec doc
        return dict(changed="spec") if v >= 2 else dict()
    if node == "spec-audit":                       # 1. = blocking finding, 2. = PASS po opravě
        if v == 1:
            return dict(outcome="FAIL", severity="blocking", returns_to="product",
                        signature="spec open-question 'created_at tz?' vs contract CLOSED")
        return dict(outcome="PASS")
    if node == "code-quality":                         # advisory finding → BEZ re-flow; zůstává hotový
        return dict(outcome="FAIL", severity="advisory",
                    signature="UserView konstruktor 4× duplikát (advisory)")
    # re-run spec-konzumentů: re-validace, ale výstup beze změny. architecture MUSÍ changed:none →
    # contract nezměněn → backend/security zůstanou valid (jádro testu).
    if node in ("feasibility", "architecture", "db-schema") and v >= 2:
        return dict(changed="none")
    return dict()

WORKERS = re.compile(r"^\s*DISPATCH\s+(\S+)")
GATEHUMAN = re.compile(r"^\s*HUMAN-GATE\s+(\S+)")
DECIDE_INTAKE = re.compile(r"DECIDE: klasifikuj '([^']+)'")
INFLIGHT_HUMAN = re.compile(r"INFLIGHT:.*?:\s*(.+?)\.")

phase = "happy"        # iteračně: dávka, kde spec-audit FAILne, je CELÁ ještě happy;
inject_next = False    # od PŘÍŠTÍ iterace = reflow
reflow_set, happy_set, humans_seen = set(), set(), set()
SAFETY = 60

for _ in range(SAFETY):
    if inject_next:
        phase = "reflow"; inject_next = False
    out = drive().stdout
    line0 = out.strip().splitlines()[0] if out.strip() else ""
    if out.startswith("DONE:") or "DONE: dosažen terminal" in out or "DONE: běh u konce" in out:
        print(f"[drive] {line0}"); break
    if out.startswith("BLOCKED") or out.startswith("HALT"):
        print(f"[drive] {line0}\n--- neočekávaný stav ---\n{out}"); sys.exit(1)
    # INFLIGHT na human-gate (l2-review zařazen do awaiting drivem, workery doběhly) → ACK
    if out.startswith("INFLIGHT"):
        mi = INFLIGHT_HUMAN.search(out)
        pend = [x.strip() for x in (mi.group(1).split(",") if mi else [])]
        acked = [n for n in pend if n in humans_seen]
        if not acked:
            print(f"[drive] INFLIGHT bez známého human-gate:\n{out}"); sys.exit(1)
        for n in acked:
            print(f"[human ] ACK {n} (spine usazena, člověk hodnotí final feature)")
            done(n, outcome="ACK")
        continue

    workers, humans, router = [], [], None
    if DECIDE_INTAKE.search(out):
        router = "intake"
    for ln in out.splitlines():
        w = WORKERS.match(ln)
        if w: workers.append(w.group(1))
        g = GATEHUMAN.match(ln)
        if g: humans.append(g.group(1)); humans_seen.add(g.group(1))
    if not (workers or humans or router):
        print(f"[drive] žádný akční uzel:\n{out}"); sys.exit(1)

    for ln in out.splitlines():
        if "↻ re-flow finding" in ln:
            print(f"   {ln.strip()}")

    # ORCHESTRAČNÍ DISCIPLÍNA: human-gate (l2-review) NEodbavuj, dokud jsou ready workery
    # (člověk hodnotí „final feature" až se spine usadí) → non-blocking l2-review nepustí
    # běh předčasně do `done`, stale spec-spine doběhne.
    if router:    todo = [(router, "router")]
    elif workers: todo = [(n, "worker") for n in workers]
    else:         todo = [(n, "human") for n in humans]

    print(f"[{phase:6}] frontier: {', '.join(n for n,_ in todo)}"
          + (f"   (odložené human-gate: {', '.join(humans)})" if humans and workers else ""))

    for node, kind in todo:
        kw = plan(node)
        cls = kw.pop("class_", None)
        if cls: kw["class"] = cls
        if kind == "human": kw.setdefault("outcome", "ACK")
        done(node, **kw)
        if kind != "human":   # human-gate = orchestrace, ne re-flow work
            (reflow_set if phase == "reflow" else happy_set).add(node)
        if node == "spec-audit" and kw.get("outcome") == "FAIL":
            inject_next = True
            print(f"   ⟵ spec-audit BLOCKING finding → re-flow od příští iterace (returns_to=product)")
else:
    print("SAFETY: překročen limit iterací"); sys.exit(1)

# ── vyhodnocení ───────────────────────────────────────────────────────────────
st = state()
EXPECTED_REFLOW = {"product", "feasibility", "architecture", "db-schema", "spec-audit"}
PROTECTED = {"backend", "qa", "performance", "security", "code-quality"}

print("\n── VÝSLEDEK ─────────────────────────────────────────────")
print("happy-path dispatch :", sorted(happy_set))
print("re-flow dispatch    :", sorted(reflow_set))
print("completed (final)   :", st.get("completed"))
print("counters            :", st.get("counters"), " status:", st.get("status"))

ok = True
if reflow_set & PROTECTED:
    print(f"❌ re-flow zasáhl CHRÁNĚNÉ uzly (kód+auditoři): {sorted(reflow_set & PROTECTED)}"); ok = False
if reflow_set - EXPECTED_REFLOW:
    print(f"❌ re-flow zasáhl NEČEKANÉ uzly: {sorted(reflow_set - EXPECTED_REFLOW)}"); ok = False
if EXPECTED_REFLOW - reflow_set:
    print(f"❌ re-flow NEzasáhl očekávané spec-konzumenty: {sorted(EXPECTED_REFLOW - reflow_set)}"); ok = False
for p in PROTECTED:
    if p not in (st.get("completed") or []):
        print(f"❌ chráněný uzel {p} není v completed (zmizel z re-flow?)"); ok = False
for need in ("backend", "qa", "architecture", "db-schema", "product"):
    if need not in happy_set:
        print(f"❌ happy-path nedispatchnul {need}"); ok = False

print("─────────────────────────────────────────────────────────")
if ok:
    print("✅ ACCEPTANCE PROŠLA: scoped re-flow drží na reálném grafu.")
    print(f"   re-flow = {len(reflow_set)} uzlů (spec spine), kód+auditoři ({len(PROTECTED)}) zůstali hotoví.")
    sys.exit(0)
print("❌ ACCEPTANCE SELHALA."); sys.exit(1)
