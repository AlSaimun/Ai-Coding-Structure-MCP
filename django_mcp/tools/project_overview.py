"""
Tool: get_project_overview

Reads and returns docs/ai_project_overview.md from the target Django project.
This file explains the project architecture, coding conventions, and layer rules
so AI tools understand the codebase before generating or reviewing code.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import PatternTool, ToolDefinition

_SCHEMA: dict = {
    "type": "object",
    "properties": {},
    "required": [],
}


class ProjectOverviewTool(PatternTool):
    """
    Returns the contents of docs/ai_project_overview.md from PROJECT_ROOT.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_project_overview",
            description=(
                "Reads and returns the project's AI overview document "
                "(docs/ai_project_overview.md). Contains architecture description, "
                "coding conventions, layer responsibilities, and design decisions. "
                "Always call this first before generating or reviewing any code."
            ),
            input_schema=_SCHEMA,
        )

    def execute(self, arguments: dict[str, Any]) -> str:
        project_root = Path(
            os.environ.get("PROJECT_ROOT") or Path(__file__).parent.parent.parent
        )
        overview_path = project_root / "docs" / "ai_project_overview.md"

        if not overview_path.exists():
            # Try the MCP server's own docs/ as fallback
            fallback = Path(__file__).parent.parent / "docs" / "ai_project_overview.md"
            if fallback.exists():
                overview_path = fallback
            else:
                return (
                    f"ai_project_overview.md not found.\n"
                    f"Expected at: {overview_path}\n\n"
                    "Create docs/ai_project_overview.md in your project root to describe "
                    "your architecture, coding rules, and conventions."
                )

        try:
            content = overview_path.read_text(encoding="utf-8")
            return f"# Project Overview\n_Source: {overview_path}_\n\n{content}"
        except Exception as exc:  # noqa: BLE001
            return f"Failed to read {overview_path}: {exc}"
