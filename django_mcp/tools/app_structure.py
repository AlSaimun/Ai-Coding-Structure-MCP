"""
Tool: get_app_structure

Scans the Django project's apps directory and returns the structure of each
Django app: which standard files/packages exist (models, services, repositories,
views, serializers, URLs, migrations, constants, admin, tests).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import PatternTool, ToolDefinition

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "app_name": {
            "type": "string",
            "description": (
                "Optional: show detailed structure for a single app, e.g. 'users'. "
                "Leave empty for a summary of all apps."
            ),
        },
    },
    "required": [],
}

# Standard files/directories we check for in each app
_STANDARD_COMPONENTS = [
    "models.py",
    "models/",
    "services.py",
    "repositories.py",
    "constants.py",
    "admin.py",
    "apps.py",
    "signals.py",
    "tasks.py",
    "tests.py",
    "tests/",
    "migrations/",
    "api/",
    "api/v1/serializers.py",
    "api/v1/views.py",
    "api/v1/urls.py",
]


def _app_component_map(app_dir: Path) -> dict[str, bool]:
    return {comp: (app_dir / comp).exists() for comp in _STANDARD_COMPONENTS}


def _find_apps(project_root: Path) -> dict[str, Path]:
    apps: dict[str, Path] = {}
    for search_dir in [project_root / "apps", project_root]:
        if not search_dir.is_dir():
            continue
        for child in sorted(search_dir.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            # Must have at least one Django app marker
            markers = ["models.py", "apps.py", "migrations"]
            if any((child / m).exists() for m in markers):
                apps[child.name] = child
    return apps


def _render_app(app_name: str, app_dir: Path, detail: bool = False) -> list[str]:
    components = _app_component_map(app_dir)
    present = [c for c, exists in components.items() if exists]
    missing = [c for c, exists in components.items() if not exists]

    lines: list[str] = [f"### `{app_name}`  —  `{app_dir}`"]
    lines.append(f"**Present ({len(present)}):** {', '.join(f'`{c}`' for c in present) or '_none_'}")

    if detail:
        lines.append(f"**Missing ({len(missing)}):** {', '.join(f'`{c}`' for c in missing) or '_none_'}")

        # List migration files count
        mig_dir = app_dir / "migrations"
        if mig_dir.is_dir():
            mig_count = len([f for f in mig_dir.glob("*.py") if f.name != "__init__.py"])
            lines.append(f"**Migrations:** {mig_count} file(s)")

        # Check for api versions
        api_dir = app_dir / "api"
        if api_dir.is_dir():
            versions = [d.name for d in sorted(api_dir.iterdir()) if d.is_dir() and not d.name.startswith("_")]
            if versions:
                lines.append(f"**API versions:** {', '.join(f'`{v}`' for v in versions)}")

    return lines


class GetAppStructureTool(PatternTool):
    """
    Scans the apps/ directory and returns the structure of each Django app.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="get_app_structure",
            description=(
                "Scans the Django project's apps directory and returns which standard "
                "components exist in each app (models, services, repositories, views, "
                "serializers, URLs, migrations, tests, etc.). "
                "Useful for understanding project layout before modifying or adding code."
            ),
            input_schema=_SCHEMA,
        )

    def execute(self, arguments: dict[str, Any]) -> str:
        project_root = Path(
            os.environ.get("PROJECT_ROOT") or Path(__file__).parent.parent.parent
        )
        filter_app: str = arguments.get("app_name", "").strip().lower()

        apps = _find_apps(project_root)
        if not apps:
            return (
                f"No Django apps detected under `{project_root}`.\n"
                "Ensure PROJECT_ROOT points to your Django project root."
            )

        lines: list[str] = [f"## App Structure — `{project_root.name}`\n"]

        for app_name, app_dir in apps.items():
            if filter_app and app_name != filter_app:
                continue
            detail = bool(filter_app) or len(apps) <= 5
            lines.extend(_render_app(app_name, app_dir, detail=detail))
            lines.append("")

        lines.append(f"**Total apps: {len(apps)}**")
        return "\n".join(lines)
