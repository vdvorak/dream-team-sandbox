---
cache_key: template-failure-signature-v1.0
type: template
---

# Failure signature (return packet) template

Šablona pro vrácení nálezu zpět vlastníkovi artefaktu (např. QA → Dev po
nálezu bugu). Jiná než standardní handoff — je to **return packet**.

Pravidla:
1. Vrácení jde **vždy přesně jeden krok zpět** k vlastníkovi artefaktu.
   QA nevolá rovnou PO; vrací Devovi a ten případně eskaluje výš.
2. **Counter `attempts`** se inkrementuje při každém vrácení v rámci wave.
   3× identická failure signature = BLOCKER eskalace na vyšší agent.
3. **Counter resetuje** pokud se failure signature změní (= je pokrok).

```yaml
---
wave: <wave-id>
from: <agent-short>           # ten kdo našel problém
returns_to: <agent-short>     # vlastník artefaktu, kterému se vrací
type: failure
attempts: <N>                 # current counter; inkrementuj při vrácení
signature_hash: <hash>        # hash z failing-check + error-type + location;
                              # používá se pro detekci „identické signature"
timestamp: <ISO-8601>
---
```

# Vrácení: <From> → <To> — <co je rozbité>

## Failure signature
```
check: <konkrétní test nebo audit kontrola>
error_type: <např. TimeoutError, AssertionError, ContractViolation>
location: <file::function nebo URL/endpoint>
expected: <co měla kontrola validovat>
actual: <co se skutečně stalo>
```

## Reproducer
Konkrétní příkaz / akce, kterou reproducuje problém:
```
<curl / pytest / krok-by-krok>
```

## Co bych nezměnil (proč si myslím, že chyba není v mém scope)
Jednou větou: co jsi zkontroloval a proč si jsi jistý, že problém je
v scope vlastníka, ne v tvém.

- Můj test / audit / spec je v pořádku, protože: ...
- Kontrakt je v pořádku, protože: ...

## Co se asi rozbilo (návrh kde hledat)
Hypotéza co opravit. Neimplementuj sám — to udělá vlastník.

- Pravděpodobně: <konkrétní hypotéza>
- Reference: <pokud existuje related rule/spec>

## === GATE OUTPUT ===
```
agent: <from-short>
phase: <T2|T3>
<main-check>: FAIL — <signature>
returns-to: <to-short>
attempts: <N>
weak-spot: <volitelné>
```
==================
