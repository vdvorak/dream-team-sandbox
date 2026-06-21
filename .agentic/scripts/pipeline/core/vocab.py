#!/usr/bin/env python3
"""vocab.py — Vocabulary: doménový obal slovníkového registru (vocabulary.yaml).

Jediný zdroj pravdy pro hodnoty, které engine rozpoznává (flagy/enumy/node_types/
edge_kinds/severities/faults/classes/targets/phases/model_tiers). Fail-closed:
neznámá hodnota = chyba, ne tichý fallback. Konzumují result.py (validace envelope),
check.py (C14/C15) a predicate.problems() (validace atomů z parsu).

Chybí-li vocabulary.yaml → `Vocabulary.missing` = True a kategorie bez fallbacku
se neověřují (SKIP, graceful) — stejná sémantika jako dřívější `load_vocabulary` → None.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_vocabulary

# Fallbacky pro běh bez registru (dřív hardcoded v result.py).
FALLBACK_SEVERITIES = ["blocking", "advisory"]
FALLBACK_MODEL_TIERS = ["haiku", "sonnet", "opus"]


class Vocabulary:
    """Read-only pohled na slovníky. Prázdné kategorie = „neověřuj" (SKIP)."""

    def __init__(self, data: dict | None, missing: bool = False) -> None:
        self._data: dict = data or {}
        self.missing = missing

    @classmethod
    def load(cls, graph_file: str) -> "Vocabulary":
        data = load_vocabulary(graph_file)
        return cls(data, missing=(data is None))

    # ── flagy (when predikáty) ────────────────────────────────────────────────
    @property
    def flags(self) -> dict:
        return self._data.get("flags", {}) or {}

    def is_known_flag(self, name: str) -> bool:
        return name in self.flags

    def flag_kind(self, name: str) -> str | None:
        """'bool' | 'enum' | None (neznámý flag)."""
        spec = self.flags.get(name)
        return (spec or {}).get("kind") if spec else None

    def enum_values(self, name: str) -> list[str]:
        return list((self.flags.get(name) or {}).get("values") or [])

    # ── ploché kategorie ──────────────────────────────────────────────────────
    def _cat(self, key: str, fallback: list[str] | None = None) -> list[str]:
        vals = self._data.get(key)
        if vals:
            return list(vals)
        return list(fallback) if fallback else []

    @property
    def targets(self) -> list[str]:
        return self._cat("targets")

    @property
    def classes(self) -> list[str]:
        return self._cat("classes")

    @property
    def faults(self) -> list[str]:
        return self._cat("faults")

    @property
    def node_types(self) -> list[str]:
        return self._cat("node_types")

    @property
    def edge_kinds(self) -> list[str]:
        return self._cat("edge_kinds")

    @property
    def phases(self) -> list[str]:
        return self._cat("phases")

    @property
    def severities(self) -> list[str]:
        return self._cat("severities", FALLBACK_SEVERITIES)

    @property
    def model_tiers(self) -> list[str]:
        return self._cat("model_tiers", FALLBACK_MODEL_TIERS)
