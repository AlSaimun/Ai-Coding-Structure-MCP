# Django MCP Server — AI Coding Intelligence

A [Model Context Protocol](https://modelcontextprotocol.io) server that gives AI coding assistants deep awareness of your Django project: its architecture, models, apps, migrations, and code quality issues.

Works with **GitHub Copilot Chat** (VS Code), **Cursor**, **Claude Code**, **Windsurf**, and any MCP-compatible client.

---

## Available Tools

| Tool | Description |
|------|-------------|
| `get_project_overview` | Reads `docs/ai_project_overview.md` — architecture, coding rules, conventions |
| `list_django_models` | Scans `apps/` and lists all model classes (static AST analysis, no Django runtime needed) |
| `get_app_structure` | Returns the file/package structure of each Django app |
| `generate_drf_api` | Generates a complete DRF scaffold: Model, Repository, Service, Serializer, Views, URLs, Constants |
| `analyze_queryset` | Analyzes an ORM queryset and suggests `select_related`, `prefetch_related`, `count()`, `exists()` optimizations |
| `list_pending_migrations` | Detects unapplied migrations via `manage.py showmigrations --plan` (falls back to static scan) |
| `detect_circular_imports` | Scans Python files, builds an import graph, and reports circular import cycles |
| `search_project_docs` | Semantic search over `docs/` (PDF + Markdown) using ChromaDB |

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | >= 3.11 |
| Virtual environment | project `venv/` |

---

## Installation

```bash
# Clone or copy django_mcp/ anywhere (global or per-project)
python3 -m venv django_mcp/venv
source django_mcp/venv/bin/activate
pip install -r django_mcp/requirements.txt
```

---

## Project Overview File

Create `docs/ai_project_overview.md` in your **Django project root** (the directory pointed to by `PROJECT_ROOT`).

**The file format is completely free-form.** The `get_project_overview` tool reads it as plain text and returns it verbatim to the AI — there is no required structure, schema, or sections. Write whatever is most useful for your project.

A minimal example is perfectly valid:

```markdown
# My Project

A platform for managing X, built with Django + DRF.

## Apps
- `users` — authentication and profiles
- `orders` — order lifecycle and payments

## Rules
- No ORM access in views — use services
- All DB queries live in repositories
- Soft delete only — never hard-delete production data
```

A detailed template is also provided at `django_mcp/docs/ai_project_overview.md` as a starting point — copy it to your project's `docs/` folder and trim or expand as needed.

Suggested topics to cover (none are mandatory):
- What the project does and its domain
- Architecture layers and their responsibilities
- Coding conventions (import order, naming, patterns)
- Key design decisions and the reasoning behind them
- List of Django apps and what each one owns
- API response shape and error codes
- Environment variables

---

## Client Configuration

### VS Code — GitHub Copilot Chat

Create `.vscode/mcp.json` in your workspace root:

```jsonc
{
  "servers": {
    "django-mcp": {
      "type": "stdio",
      "command": "${workspaceFolder}/django_mcp/venv/bin/python",
      "args": ["${workspaceFolder}/django_mcp/server.py"],
      "env": {
        "PROJECT_ROOT": "${workspaceFolder}",
        "DJANGO_SETTINGS_MODULE": "config.settings.development"
      }
    }
  }
}
```

### Cursor

Edit `~/.cursor/mcp.json`:

```jsonc
{
  "mcpServers": {
    "django-mcp": {
      "command": "/absolute/path/to/django_mcp/venv/bin/python",
      "args": ["/absolute/path/to/django_mcp/server.py"],
      "env": {
        "PROJECT_ROOT": "/absolute/path/to/your/django/project",
        "DJANGO_SETTINGS_MODULE": "config.settings.development"
      }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add django-mcp \
  --scope project \
  --env PROJECT_ROOT=/absolute/path/to/project \
  --env DJANGO_SETTINGS_MODULE=config.settings.development \
  /path/to/django_mcp/venv/bin/python \
  -- /path/to/django_mcp/server.py
```

### Windsurf

Edit `~/.codeium/windsurf/mcp_config.json`:

```jsonc
{
  "mcpServers": {
    "django-mcp": {
      "command": "/absolute/path/to/django_mcp/venv/bin/python",
      "args": ["/absolute/path/to/django_mcp/server.py"],
      "env": {
        "PROJECT_ROOT": "/absolute/path/to/project",
        "DJANGO_SETTINGS_MODULE": "config.settings.development"
      }
    }
  }
}
```

---

## Example Prompts

```
What is the architecture of this project?
```
```
List all models in the users app.
```
```
Show the structure of the payments app.
```
```
Generate a DRF API for model_name=Invoice app_name=billing with fields: number, amount, status, due_date.
```
```
Analyze this queryset: User.objects.filter(is_active=True)
```
```
Are there any pending migrations?
```
```
Detect circular imports in the apps directory.
```
```
Search project docs for how authentication is implemented.
```

---

## Project Structure

```
django_mcp/
├── server.py              # MCP entry point — thin wiring layer
├── vector_store.py        # ChromaDB indexing (PDF + Markdown)
├── requirements.txt
├── docs/
│   └── ai_project_overview.md   # starter overview template
└── tools/
    ├── __init__.py              # Registry — ALL_TOOLS
    ├── base.py                  # PatternTool ABC
    ├── project_overview.py      # get_project_overview
    ├── django_models.py         # list_django_models
    ├── app_structure.py         # get_app_structure
    ├── drf_api_generator.py     # generate_drf_api
    ├── queryset_analyzer.py     # analyze_queryset
    ├── pending_migrations.py    # list_pending_migrations
    ├── circular_imports.py      # detect_circular_imports
    └── semantic_search.py       # search_project_docs

Per-project paths (set via PROJECT_ROOT env var):
  <PROJECT_ROOT>/docs/           <- project docs (PDF + .md); read by all tools
  <PROJECT_ROOT>/.mcp_chroma/   <- vector DB, auto-created, git-ignored
```

---

## Adding a New Tool

1. Create `django_mcp/tools/my_tool.py` — subclass `PatternTool` from `base.py`.
2. Add an instance to `ALL_TOOLS` in `tools/__init__.py`.
3. Restart the MCP server.

`server.py` never needs to change.

---

## License

MIT
