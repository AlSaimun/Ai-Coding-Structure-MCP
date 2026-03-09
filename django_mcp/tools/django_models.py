"""
Tool: list_django_models

Scans the Django project's apps/ directory for model definitions by parsing
Python source files. Does not require Django to be running — pure static analysis.

Returns: dict mapping app_name → [list of model class names]
"""

from __future__ import annotations

import ast
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
                "Optional: filter by a specific app name, e.g. 'users'. "
                "Leave empty to list models for all apps."
            ),
        },
    },
    "required": [],
}

# Class bases that Django models typically inherit from
_MODEL_BASES = {
    "Model", "BaseModel", "AbstractModel", "TimeStampedModel",
    "UUIDModel", "SoftDeleteModel", "AbstractBaseUser",
}


def _extract_models_from_file(path: Path) -> list[str]:
    """
    Parse a Python file with AST and return class names that look like Django models.
    A class is considered a model if it inherits from a known model base class.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    models: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # Skip abstract / proxy metaclass markers — still list them
        bases = {
            (b.id if isinstance(b, ast.Name) else b.attr if isinstance(b, ast.Attribute) else "")
            for b in node.bases
        }
        if bases & _MODEL_BASES:
            models.append(node.name)

    return models


def _find_apps(project_root: Path) -> dict[str, Path]:
    """
    Return {app_name: app_dir} for every Django app found under apps/ or the root.
    An app is identified by the presence of models.py or a models/ package.
    """
    apps: dict[str, Path] = {}

    for search_dir in [project_root / "apps", project_root]:
        if not search_dir.is_dir():
            continue
        for child in sorted(search_dir.iterdir()):
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            has_models = (child / "models.py").exists() or (child / "models").is_dir()
            if has_models:
                apps[child.name] = child

    return apps


class ListDjangoModelsTool(PatternTool):
    """
    Lists all Django model classes found in the project by static AST analysis.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_django_models",
            description=(
                "Scans the Django project's apps directory and lists all model classes "
                "by parsing Python source files (no Django runtime required). "
                "Returns a map of app_name → [model names]. "
                "Optionally filter to a single app with the 'app_name' parameter."
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
                f"No Django apps found under {project_root}.\n"
                "Ensure PROJECT_ROOT points to your Django project root and apps "
                "are in an apps/ directory or directly at the root."
            )

        lines: list[str] = [f"## Django Models — `{project_root.name}`\n"]
        total = 0

        for app_name, app_dir in apps.items():
            if filter_app and app_name != filter_app:
                continue

            # Collect model files
            model_files: list[Path] = []
            models_py = app_dir / "models.py"
            models_pkg = app_dir / "models"
            if models_py.exists():
                model_files.append(models_py)
            elif models_pkg.is_dir():
                model_files.extend(sorted(models_pkg.glob("*.py")))

            model_names: list[str] = []
            for mf in model_files:
                model_names.extend(_extract_models_from_file(mf))

            if model_names:
                lines.append(f"### `{app_name}`")
                for name in model_names:
                    lines.append(f"  - `{name}`")
                total += len(model_names)
            else:
                lines.append(f"### `{app_name}` _(no models detected)_")

        lines.append(f"\n**Total models found: {total}**")
        return "\n".join(lines)
