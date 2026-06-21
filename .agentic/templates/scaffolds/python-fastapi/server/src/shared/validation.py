from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Result of the validation-only (dry-run) mode of a write endpoint (rules/backend.md §Write-flow).

    `valid=True` ⇔ empty `field_errors`. Commit (`?validate=false`) does NOT rely on the
    client having called this — it re-validates server-side. The client calls dry-run only
    for live UX hints (rules/frontend.md §Write-flow).
    """

    valid: bool
    field_errors: dict[str, str] = {}

    @classmethod
    def of(cls, field_errors: dict[str, str]) -> "ValidationResult":
        return cls(valid=not field_errors, field_errors=field_errors)
