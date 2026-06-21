# Backlog: Watson „self-host" režim (flow-improvement)

**Třída:** improvement · **Stav:** ✅ FIXED · **Priorita:** —

**Fix:** mechanická část = skript `scripts/pipeline/core/self_host_init.py` (+ `self-host-init.sh`):
detekuje self-host (TOOL na rootu bez `.agentic/`), idempotentně seedne PRODUCT vrstvu
(`project-config` s `active_roles` odvozenými z grafu + `project_type: self-host`,
`PROJECT-CONSTITUTION`/`STATE`/`current-run` + `backlog/`/`handoffs/`), TODO značky (vize/targety)
nechá interview. Watson kontrakt rozšířen o detekci „Self-host" + recept (`agents/watson-interviewer.md
§Self-host`). Inverze `structure-check` (vytvoří ↔ ověří): round-trip seed→structure-check projde
(selftest). Zbylá pozn.: dual-role `rules/` — needuplikovat (zdokumentováno v project-config).

## Co
Watson umí greenfield (prázdný adresář → setup) a transition (ne-agentic projekt → přidá
`.agentic/`). **Neumí** onboardovat sám framework — když je projekt zároveň nástroj
(self-reference: „kde je `.agentic/`? … to jsem já?"). Doplnit třetí režim: **self-host**
= dát frameworku PRODUCT vrstvu (PROJECT-CONSTITUTION + project-config + backlog + current-run)
bez klonování `.agentic/` (TOOL vrstva je sám repo).

## Proč
Vyšlo z dogfoodingu: převod frameworku na standardní projekt (wave `2026-06-13-self-host-framework`)
jsme museli udělat manuálně, protože Watson tenhle case neumí. Až bude umět, příště konverzi
(i pro budoucí self-hostované nástroje) zvládne flow.

## Scope (hrubě)
- Watson detekce stavu: rozšířit o `self-host` (root má `constitution.md`/`agents/`/`pipeline/` =
  je to framework, ne projekt, co ho konzumuje).
- Seed PRODUCT vrstvy odvozený z TOOL vrstvy (vize z `PROJECT-CONSTITUTION`; active_roles z toho, co repo reálně dělá).
- Pozn. dual-role `rules/` (universal zdroj i projektový overlay) — vyřešit, ať to nekoliduje.

## Reference
Manuální provedení = wave `handoffs/2026-06-13-self-host-framework/`.
