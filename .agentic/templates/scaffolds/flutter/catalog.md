# Mobile widget catalog (flutter)

Shared building blocks, které kostra veze. **Než vytvoříš widget, koukni sem; existuje-li
odpovídající, MUSÍ se použít** (constitution §Reuse policy — raw varianta = drift). Katalog
**roste** přes Extraction Candidates (`templates/extraction-candidates.md`): 2. výskyt patternu
→ `extract-shared` + **back-fill všech výskytů**.

| Block | Kdy použít | Kde |
|---|---|---|
| `ApiError` | doménová chyba `{code, details}` | `lib/src/shared/api_error.dart` |
| `api_client` | dio + auth/error interceptor | `lib/src/shared/api_client.dart` |
| `FormModelController` / `FormFieldBinding` | write formulář (dry-run validate → commit) | `lib/src/shared/form_model.dart` |
| example slice (`model → repository → controller → page`) | vzor vertical slice | `lib/src/example/` |

Startovní katalog — projekt rozšiřuje, jak extrahuje opakované widgety.

## Conformance (mechanický back-align)

`catalog-conformance.yaml` deklaruje anti-pattern signatury; `scripts/catalog-conformance.sh`
je vynucuje ve Vitek gate. Při extrakci widgetu přidej jeho signaturu (raw forma) → scan
vynutí migraci všech míst.
