"""
Tool: detect_circular_imports

Scans the Django project's Python source files, builds an import dependency graph,
and detects circular import cycles using depth-first search.

Only intra-project imports are analysed (stdlib and third-party packages are ignored).
"""

from __future__ import annotations

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from .base import PatternTool, ToolDefinition

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "directory": {
            "type": "string",
            "description": (
                "Optional sub-directory relative to PROJECT_ROOT to scan, e.g. 'apps'. "
                "Defaults to scanning the entire project root."
            ),
        },
        "max_cycles": {
            "type": "integer",
            "description": "Maximum number of cycles to report (default 10).",
            "default": 10,
            "minimum": 1,
            "maximum": 50,
        },
    },
    "required": [],
}

# ── Import parsing ─────────────────────────────────────────────────────────────

def _get_imports(path: Path, project_root: Path) -> list[str]:
    """
    Parse a Python file and return a list of intra-project module paths
    (dot-separated) that this file imports from.
    We skip stdlib / third-party by checking if the module root exists as a
    directory or .py file relative to project_root.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                if _is_project_module(mod, project_root):
                    imports.append(mod)

        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            # Relative imports
            if node.level and node.level > 0:
                # Convert relative to absolute based on the current file's package
                try:
                    pkg_parts = path.relative_to(project_root).with_suffix("").parts
                    up = node.level
                    base_parts = pkg_parts[:-up] if up < len(pkg_parts) else ()
                    mod = ".".join(list(base_parts) + ([node.module] if node.module else []))
                    imports.append(mod)
                except ValueError:
                    pass
            else:
                mod = node.module
                if _is_project_module(mod, project_root):
                    imports.append(mod)

    return imports


def _is_project_module(mod: str, project_root: Path) -> bool:
    """
    Return True if the top-level package of `mod` corresponds to a directory
    or .py file in the project root (i.e. it's a local module, not stdlib/third-party).
    """
    top = mod.split(".")[0]
    return (project_root / top).is_dir() or (project_root / f"{top}.py").exists()


def _file_to_module(path: Path, project_root: Path) -> str:
    """Convert a file path to a dotted module string."""
    try:
        rel = path.relative_to(project_root).with_suffix("")
        return ".".join(rel.parts)
    except ValueError:
        return str(path)


# ── Graph building ─────────────────────────────────────────────────────────────

def _build_graph(scan_root: Path, project_root: Path) -> dict[str, list[str]]:
    """
    Return {module: [imported_modules]} for all Python files under scan_root.
    """
    graph: dict[str, list[str]] = defaultdict(list)
    for py_file in sorted(scan_root.rglob("*.py")):
        if any(part.startswith((".", "__pycache__")) for part in py_file.parts):
            continue
        mod = _file_to_module(py_file, project_root)
        for imp in _get_imports(py_file, project_root):
            graph[mod].append(imp)
    return dict(graph)


# ── Cycle detection (DFS) ─────────────────────────────────────────────────────

def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """
    Find all simple cycles in a directed graph using iterative DFS.
    Returns a list of cycles, where each cycle is a list of module names.
    """
    visited: set[str] = set()
    cycles: list[list[str]] = []
    all_nodes = set(graph.keys()) | {dep for deps in graph.values() for dep in deps}

    def dfs(node: str, path: list[str], path_set: set[str]) -> None:
        if len(cycles) >= 50:  # hard cap
            return
        for neighbour in graph.get(node, []):
            if neighbour in path_set:
                # Found a cycle — extract the cycle portion
                idx = path.index(neighbour)
                cycle = path[idx:] + [neighbour]
                # Normalise to avoid duplicate cycles with different start points
                cycle_key = tuple(sorted(cycle))
                if not any(tuple(sorted(c)) == cycle_key for c in cycles):
                    cycles.append(cycle)
            elif neighbour not in visited and neighbour in graph:
                path.append(neighbour)
                path_set.add(neighbour)
                dfs(neighbour, path, path_set)
                path.pop()
                path_set.discard(neighbour)

    for node in all_nodes:
        if node not in visited and node in graph:
            visited.add(node)
            dfs(node, [node], {node})

    return cycles


class DetectCircularImportsTool(PatternTool):
    """
    Scans project Python files and detects circular import patterns.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="detect_circular_imports",
            description=(
                "Scans the Django project's Python files, builds an import graph, "
                "and detects circular import cycles using depth-first search. "
                "Reports cycles with the chain of modules involved and suggests fixes. "
                "Only intra-project imports are analysed (stdlib/third-party ignored)."
            ),
            input_schema=_SCHEMA,
        )

    def execute(self, arguments: dict[str, Any]) -> str:
        project_root = Path(
            os.environ.get("PROJECT_ROOT") or Path(__file__).parent.parent.parent
        )
        sub_dir: str = arguments.get("directory", "").strip()
        max_cycles: int = min(int(arguments.get("max_cycles", 10)), 50)

        scan_root = project_root / sub_dir if sub_dir else project_root

        if not scan_root.is_dir():
            return f"Directory not found: `{scan_root}`"

        graph = _build_graph(scan_root, project_root)
        if not graph:
            return (
                f"No Python files with intra-project imports found under `{scan_root}`.\n"
                "Ensure PROJECT_ROOT is set correctly."
            )

        cycles = _find_cycles(graph)[:max_cycles]

        lines: list[str] = [
            f"## Circular Import Analysis — `{scan_root.relative_to(project_root) if sub_dir else project_root.name}`",
            "",
            f"_Scanned {len(graph)} module(s) with intra-project imports._",
            "",
        ]

        if not cycles:
            lines.append("✅ **No circular imports detected.**")
            return "\n".join(lines)

        lines.append(f"🔴 **{len(cycles)} circular import cycle(s) found:**")
        lines.append("")

        for i, cycle in enumerate(cycles, 1):
            chain = " → ".join(f"`{m}`" for m in cycle)
            lines.append(f"### Cycle {i}")
            lines.append(chain)
            lines.append("")

        lines.append("---")
        lines.append("### How to Fix Circular Imports")
        lines.append("")
        lines.append(
            "1. **Lazy imports** — move the import inside the function/method body that needs it:"
        )
        lines.append("   ```python")
        lines.append("   def my_func():")
        lines.append("       from apps.other_app.models import OtherModel  # lazy")
        lines.append("   ```")
        lines.append(
            "2. **Extract shared code** — move shared logic to a third module that neither "
            "circular participant imports from."
        )
        lines.append(
            "3. **Use `TYPE_CHECKING`** — for type-hint-only imports:"
        )
        lines.append("   ```python")
        lines.append("   from __future__ import annotations")
        lines.append("   from typing import TYPE_CHECKING")
        lines.append("   if TYPE_CHECKING:")
        lines.append("       from apps.other_app.models import OtherModel")
        lines.append("   ```")
        lines.append(
            "4. **Refactor service/repository layers** — services should only import "
            "from repositories and models, not from other services."
        )

        return "\n".join(lines)
