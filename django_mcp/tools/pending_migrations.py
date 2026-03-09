"""
Tool: list_pending_migrations

Detects unapplied (pending) migrations in the Django project by:
  1. Running `python manage.py showmigrations --plan` via subprocess (preferred).
  2. Falling back to static file scanning if the Django environment isn't available.

Requires PROJECT_ROOT to point to the Django project root.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .base import PatternTool, ToolDefinition

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "app_name": {
            "type": "string",
            "description": (
                "Optional: check migrations only for a specific app, e.g. 'users'. "
                "Leave empty to check all apps."
            ),
        },
    },
    "required": [],
}


def _run_manage_py(project_root: Path, app_name: str) -> tuple[bool, str]:
    """
    Try to run `python manage.py showmigrations --plan` in the project root.
    Returns (success, output_text).
    """
    manage_py = project_root / "manage.py"
    if not manage_py.exists():
        return False, f"`manage.py` not found at `{project_root}`."

    # Use the same Python interpreter that is running the MCP server
    python_exe = sys.executable

    cmd = [python_exe, str(manage_py), "showmigrations", "--plan"]
    if app_name:
        cmd.append(app_name)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(project_root),
        )
        if result.returncode == 0:
            return True, result.stdout
        return False, result.stderr or result.stdout
    except FileNotFoundError:
        return False, f"Python executable not found: `{python_exe}`"
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 30 seconds."
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _parse_pending_from_plan(output: str) -> list[str]:
    """
    Parse `showmigrations --plan` output and return lines with [ ] (unapplied).
    Applied migrations have [X], pending have [ ].
    """
    pending: list[str] = []
    for line in output.splitlines():
        if re.search(r"\[\s\]", line):
            pending.append(line.strip())
    return pending


def _static_scan(project_root: Path, app_name: str) -> str:
    """
    Fallback: scan migrations directories and report how many files exist per app.
    Cannot determine applied status without a DB connection.
    """
    apps_dirs = [project_root / "apps", project_root]
    lines: list[str] = [
        "⚠️  _Could not run `manage.py` — showing static migration file counts._",
        "_(To see actual pending migrations, ensure PROJECT_ROOT and DJANGO_SETTINGS_MODULE are set correctly.)_",
        "",
    ]

    found_any = False
    for search_dir in apps_dirs:
        if not search_dir.is_dir():
            continue
        for child in sorted(search_dir.iterdir()):
            if app_name and child.name != app_name:
                continue
            mig_dir = child / "migrations"
            if not mig_dir.is_dir():
                continue
            mig_files = [f for f in sorted(mig_dir.glob("*.py")) if f.name != "__init__.py"]
            if mig_files:
                lines.append(f"### `{child.name}` — {len(mig_files)} migration file(s)")
                for mf in mig_files:
                    lines.append(f"  - `{mf.name}`")
                found_any = True

    if not found_any:
        lines.append("No migration directories found.")
    return "\n".join(lines)


class ListPendingMigrationsTool(PatternTool):
    """
    Lists pending (unapplied) Django migrations using manage.py or static file scanning.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_pending_migrations",
            description=(
                "Detects pending (unapplied) migrations in the Django project by running "
                "`manage.py showmigrations --plan`. Falls back to static migration file "
                "scanning if Django can't be loaded. Requires PROJECT_ROOT to be set. "
                "Useful before deploying to check if `manage.py migrate` is needed."
            ),
            input_schema=_SCHEMA,
        )

    def execute(self, arguments: dict[str, Any]) -> str:
        project_root = Path(
            os.environ.get("PROJECT_ROOT") or Path(__file__).parent.parent.parent
        )
        app_name: str = arguments.get("app_name", "").strip()

        lines: list[str] = [
            f"## Pending Migrations — `{project_root.name}`",
            "",
        ]

        success, output = _run_manage_py(project_root, app_name)

        if success:
            pending = _parse_pending_from_plan(output)
            if pending:
                lines.append(f"🔴 **{len(pending)} pending migration(s) detected:**")
                lines.append("")
                for p in pending:
                    lines.append(f"  - `{p}`")
                lines.append("")
                lines.append("**Run:** `python manage.py migrate` to apply.")
            else:
                lines.append("✅ **All migrations are applied.** No pending migrations found.")
                lines.append("")
                # Show full plan for reference
                applied = [l for l in output.splitlines() if re.search(r"\[X\]", l)]
                if applied:
                    lines.append(f"_(Total applied: {len(applied)} migrations)_")
        else:
            lines.append(_static_scan(project_root, app_name))
            lines.append("")
            lines.append(f"**Django error:** `{output.strip()[:500]}`")

        return "\n".join(lines)
