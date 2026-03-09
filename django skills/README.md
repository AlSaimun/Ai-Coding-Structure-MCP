# Django Coding Skills

Reusable AI coding skills that enforce this project's Django service-layer architecture.  
Each skill is a structured prompt that tells the AI assistant exactly how to generate or fix code following the project's conventions.

---

## Available Skills

| Skill | Trigger phrase examples |
|-------|------------------------|
| `create-feature` | _"create a full feature for Invoice"_, _"add a complete CRUD for Order"_ |
| `create-model` | _"create a model for Product"_, _"add a database table for Category"_ |
| `create-repository` | _"create a repository for User"_, _"add data access layer for Payment"_ |
| `create-service` | _"create a service for Subscription"_, _"add business logic for Refund"_ |
| `create-serializer` | _"create a serializer for Invoice"_, _"add DRF serializer for Profile"_ |
| `create-view` | _"create a view for Order"_, _"add an API endpoint for Report"_ |
| `fix-coding-structure` | _"fix the coding structure in this file"_, _"audit views.py for violations"_ |

---

## Setup by Tool

### GitHub Copilot (VS Code)

Copilot loads skills from `.github/skills/` in your repository root.

```
your-django-project/
└── .github/
    └── skills/
        ├── create-feature/
        │   └── SKILL.md
        ├── create-model/
        │   └── SKILL.md
        ├── create-repository/
        │   └── SKILL.md
        ├── create-service/
        │   └── SKILL.md
        ├── create-serializer/
        │   └── SKILL.md
        ├── create-view/
        │   └── SKILL.md
        └── fix-coding-structure/
            └── SKILL.md
```

**Steps:**
1. Copy the skill folders into `.github/skills/` in your Django project root.
2. Commit and push.
3. Open **Copilot Chat** in VS Code, switch to **Agent** mode.
4. Invoke a skill using the `/` slash command followed by the skill name and your arguments:

```
/create-model users UserProfile name email is_verified
/create-service billing Invoice
/create-feature orders Order product_id quantity status
/create-repository payments Payment
/create-serializer users UserProfile
/create-view products Product
/fix-coding-structure apps/users/api/v1/views/user_view.py
```

---

### Cursor

Cursor reads instruction files from `.cursor/rules/` in your project root.  
Each SKILL.md becomes a separate `.mdc` rule file.

```
your-django-project/
└── .cursor/
    └── rules/
        ├── create-feature.mdc
        ├── create-model.mdc
        ├── create-repository.mdc
        ├── create-service.mdc
        ├── create-serializer.mdc
        ├── create-view.mdc
        └── fix-coding-structure.mdc
```

**Steps:**
1. Copy each `SKILL.md` content into a corresponding `.mdc` file under `.cursor/rules/`.
2. In Cursor Settings → **Rules for AI**, verify the rules appear.
3. Apply rules either globally or per file type (e.g. `*.py` only).
4. In Cursor Chat, mention the rule name or describe the task — Cursor applies the matching rule automatically.

---

### Continue

Continue reads context rules from `.continue/rules/` in your project root.

```
your-django-project/
└── .continue/
    └── rules/
        ├── create-feature.md
        ├── create-model.md
        ├── create-repository.md
        ├── create-service.md
        ├── create-serializer.md
        ├── create-view.md
        └── fix-coding-structure.md
```

**Steps:**
1. Copy each `SKILL.md` as a `.md` file under `.continue/rules/`.
2. Restart Continue (or reload the window).
3. Continue will automatically include matching rules based on context, or you can reference them with `@rules` in the chat.

---

### Kiro (Amazon)

Kiro reads steering documents from `.kiro/steering/` in your project root.

```
your-django-project/
└── .kiro/
    └── steering/
        ├── create-feature.md
        ├── create-model.md
        ├── create-repository.md
        ├── create-service.md
        ├── create-serializer.md
        ├── create-view.md
        └── fix-coding-structure.md
```

**Steps:**
1. Copy each `SKILL.md` as a `.md` file under `.kiro/steering/`.
2. Kiro automatically picks up steering files on startup — no restart needed.
3. Files in `steering/` are always active; Kiro includes them as persistent context in every conversation.

---

### Windsurf

Windsurf reads rules from `.windsurf/rules/` in your project root.

```
your-django-project/
└── .windsurf/
    └── rules/
        ├── create-feature.md
        ├── create-model.md
        ├── create-repository.md
        ├── create-service.md
        ├── create-serializer.md
        ├── create-view.md
        └── fix-coding-structure.md
```

**Steps:**
1. Copy each `SKILL.md` as a `.md` file under `.windsurf/rules/`.
2. Open **Cascade** and the rules will be active in every conversation automatically.
3. You can also use `@rules` in Cascade chat to reference a specific rule by name.

---

### Antigravity (Gemini Code Assist)

Antigravity reads context files from `.gemini/` in your project root.

```
your-django-project/
└── .gemini/
    └── skills/
        ├── create-feature.md
        ├── create-model.md
        ├── create-repository.md
        ├── create-service.md
        ├── create-serializer.md
        ├── create-view.md
        └── fix-coding-structure.md
```

**Steps:**
1. Copy each `SKILL.md` as a `.md` file under `.gemini/skills/`.
2. In your `.gemini/config.yaml` (create it if missing), reference the skills directory:
   ```yaml
   context_files:
     - .gemini/skills/*.md
   ```
3. Restart Antigravity — the skills will be included as context in every session.

---

## Quick Copy Script

Run this from your Django project root to copy all skills into the right place for every tool at once:

```bash
SKILLS_SOURCE="/path/to/this/django-skills-directory"

# GitHub Copilot
mkdir -p .github/skills
for skill in create-feature create-model create-repository create-service create-serializer create-view fix-coding-structure; do
  mkdir -p ".github/skills/$skill"
  cp "$SKILLS_SOURCE/$skill/SKILL.md" ".github/skills/$skill/SKILL.md"
done

# Cursor
mkdir -p .cursor/rules
for skill in create-feature create-model create-repository create-service create-serializer create-view fix-coding-structure; do
  cp "$SKILLS_SOURCE/$skill/SKILL.md" ".cursor/rules/$skill.mdc"
done

# Continue
mkdir -p .continue/rules
for skill in create-feature create-model create-repository create-service create-serializer create-view fix-coding-structure; do
  cp "$SKILLS_SOURCE/$skill/SKILL.md" ".continue/rules/$skill.md"
done

# Kiro
mkdir -p .kiro/steering
for skill in create-feature create-model create-repository create-service create-serializer create-view fix-coding-structure; do
  cp "$SKILLS_SOURCE/$skill/SKILL.md" ".kiro/steering/$skill.md"
done

# Windsurf
mkdir -p .windsurf/rules
for skill in create-feature create-model create-repository create-service create-serializer create-view fix-coding-structure; do
  cp "$SKILLS_SOURCE/$skill/SKILL.md" ".windsurf/rules/$skill.md"
done

# Antigravity
mkdir -p .gemini/skills
for skill in create-feature create-model create-repository create-service create-serializer create-view fix-coding-structure; do
  cp "$SKILLS_SOURCE/$skill/SKILL.md" ".gemini/skills/$skill.md"
done

echo "Done — skills copied for all tools."
```

---

## How Skills Work

Each `SKILL.md` is a structured Markdown file with a YAML front-matter header:

```yaml
---
name: create-model
description: When to activate this skill (used by the AI to auto-select it)
argument-hint: <AppName> <ModelName> [field descriptions]
---
```

The body contains step-by-step instructions, templates, rules, and examples that the AI follows when the skill is active. The content is tool-agnostic — the same file works across all tools listed above.

---

## Adding a New Skill

1. Create a new folder here: `your-skill-name/SKILL.md`
2. Add the YAML front-matter (`name`, `description`, `argument-hint`)
3. Write the instructions, template, rules, and examples in Markdown
4. Re-run the copy script above to deploy it to all tools
