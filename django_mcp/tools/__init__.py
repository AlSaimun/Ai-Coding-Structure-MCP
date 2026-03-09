"""
Tool registry — single place to register every tool.

To add a new tool:
  1. Create django_mcp/tools/my_tool.py  (subclass PatternTool)
  2. Import it here and append an instance to ALL_TOOLS.
  Nothing else changes.  (Open/Closed Principle)
"""

from __future__ import annotations

# ── Import every tool class ───────────────────────────────────────────────────

from .project_overview   import ProjectOverviewTool
from .django_models      import ListDjangoModelsTool
from .app_structure      import GetAppStructureTool
from .drf_api_generator  import GenerateDrfApiTool
from .queryset_analyzer  import AnalyzeQuerysetTool
from .pending_migrations import ListPendingMigrationsTool
from .circular_imports   import DetectCircularImportsTool
from .semantic_search    import SemanticSearchTool

# ── Build registry ────────────────────────────────────────────────────────────

ALL_TOOLS = [
    # ── Project intelligence tools
    ProjectOverviewTool(),
    ListDjangoModelsTool(),
    GetAppStructureTool(),
    # ── Code generation
    GenerateDrfApiTool(),
    # ── Analysis & diagnostics
    AnalyzeQuerysetTool(),
    ListPendingMigrationsTool(),
    DetectCircularImportsTool(),
    # ── Semantic search over project docs (ChromaDB)
    SemanticSearchTool(),
]
