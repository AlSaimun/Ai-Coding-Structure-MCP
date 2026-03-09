"""
Tool: analyze_queryset

Accepts a queryset string and performs static analysis to suggest:
  - select_related() for ForeignKey / OneToOne fields (avoids N+1 via JOIN)
  - prefetch_related() for ManyToMany / reverse FK (avoids N+1 via separate query)
  - only() / defer() for large field sets
  - General ORM anti-patterns

No Django runtime is needed — analysis is purely textual/pattern-based.
"""

from __future__ import annotations

import re
from typing import Any

from .base import PatternTool, ToolDefinition

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "queryset": {
            "type": "string",
            "description": (
                "A Django ORM queryset expression (one or multiple lines). "
                "Example: \"User.objects.filter(is_active=True)\""
            ),
        },
        "model_name": {
            "type": "string",
            "description": "Optional model name for more targeted suggestions (e.g. 'User').",
        },
    },
    "required": ["queryset"],
}

# ── Rules ─────────────────────────────────────────────────────────────────────

_ISSUES = [
    {
        "pattern": r"\.(filter|exclude|get|first|last|all)\(",
        "no_select_related": True,
        "message": (
            "No `select_related()` detected. If the queryset accesses ForeignKey or "
            "OneToOneField attributes later (e.g. `user.profile`), add "
            "`.select_related('profile')` to avoid N+1 queries (Django does a JOIN)."
        ),
        "severity": "warning",
    },
    {
        "pattern": r"\.(filter|exclude|get|first|last|all)\(",
        "no_prefetch_related": True,
        "message": (
            "No `prefetch_related()` detected. If the queryset accesses ManyToManyField "
            "or reverse FK relations later (e.g. `order.items.all()`), add "
            "`.prefetch_related('items')` to avoid N+1 queries (Django does a second query)."
        ),
        "severity": "info",
    },
    {
        "pattern": r"\.objects\.all\(\)",
        "message": (
            "`.objects.all()` fetches every row with all columns. "
            "Add `.only('field1', 'field2')` to SELECT only needed columns, "
            "or `.filter(...)` to limit rows. Avoid loading the full table."
        ),
        "severity": "warning",
    },
    {
        "pattern": r"\.values_list\(",
        "no_flat": True,
        "message": (
            "`.values_list()` without `flat=True` returns tuples. "
            "If you only need a single field, use `.values_list('field', flat=True)` "
            "to get a plain list."
        ),
        "severity": "info",
    },
    {
        "pattern": r"len\(",
        "message": (
            "Using `len(queryset)` evaluates the entire queryset and loads it into memory. "
            "Use `queryset.count()` instead — it executes a `SELECT COUNT(*)` query."
        ),
        "severity": "error",
    },
    {
        "pattern": r"if\s+queryset\b|if\s+qs\b",
        "message": (
            "Using a queryset in a boolean context (`if queryset`) loads all rows. "
            "Use `queryset.exists()` instead for an efficient `SELECT 1` check."
        ),
        "severity": "warning",
    },
    {
        "pattern": r"for\s+\w+\s+in\s+.*\.objects\.",
        "message": (
            "Iterating over a raw queryset in a loop without prior `.select_related()` / "
            "`.prefetch_related()` is a common N+1 pattern. Ensure relations accessed "
            "inside the loop are prefetched."
        ),
        "severity": "warning",
    },
    {
        "pattern": r"\.order_by\(['\"](?!-)",
        "message": (
            "Ordering by a field without an index can cause full-table sorts. "
            "Ensure the order_by field has a `db_index=True` or is part of a composite index."
        ),
        "severity": "info",
    },
    {
        "pattern": r"\[0\]|\[:\d+\]",
        "no_limit": True,
        "message": (
            "Slicing a queryset with `[0]` or `[:n]` is fine, but make sure you're not "
            "slicing an unevaluated queryset inside a loop. Prefer `.first()` or `.last()` "
            "for single objects — they use `LIMIT 1`."
        ),
        "severity": "info",
    },
]


def _check_select_related(qs: str) -> bool:
    return bool(re.search(r"select_related\(", qs))


def _check_prefetch_related(qs: str) -> bool:
    return bool(re.search(r"prefetch_related\(", qs))


def _check_values_list_flat(qs: str) -> bool:
    m = re.search(r"values_list\(", qs)
    if not m:
        return True  # not used
    return bool(re.search(r"flat\s*=\s*True", qs))


class AnalyzeQuerysetTool(PatternTool):
    """
    Analyzes a Django ORM queryset string and suggests performance optimizations.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_queryset",
            description=(
                "Analyzes a Django ORM queryset expression and suggests optimizations: "
                "select_related() for FK/OneToOne relations (JOIN), "
                "prefetch_related() for M2M/reverse FK (separate query), "
                "count() over len(), exists() over bool check, "
                "and other common N+1 / performance anti-patterns."
            ),
            input_schema=_SCHEMA,
        )

    def execute(self, arguments: dict[str, Any]) -> str:
        qs: str = arguments.get("queryset", "").strip()
        model_name: str = arguments.get("model_name", "").strip()

        if not qs:
            return "Please provide a non-empty queryset string."

        findings: list[dict] = []

        has_select_related = _check_select_related(qs)
        has_prefetch_related = _check_prefetch_related(qs)
        has_flat = _check_values_list_flat(qs)

        for rule in _ISSUES:
            pattern = rule["pattern"]
            if not re.search(pattern, qs, re.IGNORECASE):
                continue

            # Skip select_related check if already present
            if rule.get("no_select_related") and has_select_related:
                continue
            # Skip prefetch_related check if already present
            if rule.get("no_prefetch_related") and has_prefetch_related:
                continue
            # Skip flat check if already present
            if rule.get("no_flat") and has_flat:
                continue

            findings.append({"severity": rule["severity"], "message": rule["message"]})

        # ── Build output ──────────────────────────────────────────────────────────
        lines: list[str] = []
        model_label = f" for `{model_name}`" if model_name else ""
        lines.append(f"## Queryset Analysis{model_label}")
        lines.append("")
        lines.append("**Input:**")
        lines.append("```python")
        lines.append(qs)
        lines.append("```")
        lines.append("")

        if not findings:
            lines.append("✅ **No issues detected.** The queryset looks well-optimized.")
            return "\n".join(lines)

        severity_order = {"error": 0, "warning": 1, "info": 2}
        findings.sort(key=lambda f: severity_order.get(f["severity"], 3))

        icons = {"error": "🔴", "warning": "🟡", "info": "🔵"}
        lines.append(f"**{len(findings)} suggestion(s) found:**")
        lines.append("")

        for i, f in enumerate(findings, 1):
            icon = icons.get(f["severity"], "•")
            lines.append(f"{i}. {icon} **{f['severity'].upper()}** — {f['message']}")
            lines.append("")

        # ── Optimization example ──────────────────────────────────────────────────
        lines.append("---")
        lines.append("### Optimized Queryset Example")
        lines.append("```python")
        optimized = qs.rstrip(")")
        if not has_select_related:
            optimized += "\n    .select_related('related_field')   # replace with actual FK field names"
        if not has_prefetch_related:
            optimized += "\n    .prefetch_related('m2m_field')      # replace with actual M2M / reverse FK field names"
        optimized += "\n)"
        lines.append(optimized)
        lines.append("```")

        lines.append("")
        lines.append(
            "**Tip:** Use Django Debug Toolbar or `connection.queries` in tests "
            "to verify the number of SQL queries before/after."
        )

        return "\n".join(lines)
