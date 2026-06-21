from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiListOf(BaseModel, Generic[T]):
    """Plain collection without pagination metadata (rules/backend.md §Kolekce)."""

    items: list[T]


class ApiPageOf(BaseModel, Generic[T]):
    """Offset/page collection — when the user needs a total count / jump to a page."""

    items: list[T]
    total: int
    page: int
    page_size: int


class ApiSliceOf(BaseModel, Generic[T]):
    """Slice for infinite scroll — cursor + has_more; no total or page index.

    `next_cursor` is stable (ordering + tie-breaker, typically id), not an opaque blob.
    """

    items: list[T]
    has_more: bool
    next_cursor: str | None = None
