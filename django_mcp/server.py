#!/usr/bin/env python3
"""
MCP Server — ai-agents-backend Coding Structure
================================================
Entry point only. All business logic lives in:
  django_mcp/tools/       ← one file per tool
  django_mcp/resources.py ← resource definitions

To add a new tool: create a file in tools/ and register it in tools/__init__.py.
This file never needs to change.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# ── MCP SDK ───────────────────────────────────────────────────────────────────
try:
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel.server import NotificationOptions
except ImportError:
    print("ERROR: mcp package not found. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# ── Local modules (tools/ and resources.py are siblings of this file) ─────────
#    We add the django_mcp/ directory itself to sys.path so `import tools` works,
#    but do NOT add the project root (that would shadow the installed mcp SDK).
sys.path.insert(0, str(Path(__file__).parent))

from tools import ALL_TOOLS                  # noqa: E402
from vector_store import init_store          # noqa: E402

# ── Resolve project root ──────────────────────────────────────────────────────
#   Priority: PROJECT_ROOT env var  →  parent of django_mcp/ (i.e. this file's grandparent)
#   VS Code sets PROJECT_ROOT=${workspaceFolder} via .vscode/mcp.json
#   Cursor / Claude Code / Windsurf set it the same way in their config files
_PROJECT_ROOT = os.environ.get("PROJECT_ROOT") or str(Path(__file__).parent.parent)

# ── Eager PDF indexing — runs before the server accepts any connections ────────
print(f"[MCP] Project root : {_PROJECT_ROOT}", file=sys.stderr, flush=True)
print("[MCP] Indexing project docs...", file=sys.stderr, flush=True)
try:
    _store = init_store(_PROJECT_ROOT)
    count = _store.doc_count()
    files = _store.indexed_files()
    if count:
        print(f"[MCP] Indexed {count} chunk(s) from: {', '.join(files)}", file=sys.stderr, flush=True)
    else:
        print(f"[MCP] No docs found in {_PROJECT_ROOT}/docs/ — add .pdf or .md files there and restart.", file=sys.stderr, flush=True)
except Exception as exc:
    print(f"[MCP] WARNING: PDF indexing failed — {exc}", file=sys.stderr, flush=True)

# ── Entry point ───────────────────────────────────────────────────────────────
async def main() -> None:
    # Fresh Server instance per connection — prevents "Already connected to a
    # transport" error when clients like Continue or VS Code reconnect.
    server = Server("ai-agents-coding-structure")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [tool.to_mcp_tool() for tool in ALL_TOOLS]

    _TOOL_REGISTRY = {tool.definition.name: tool for tool in ALL_TOOLS}

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        tool = _TOOL_REGISTRY.get(name)
        if tool is None:
            return [types.TextContent(type="text", text=f"Unknown tool: '{name}'")]
        return tool.to_mcp_content(arguments)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ai-agents-coding-structure",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
