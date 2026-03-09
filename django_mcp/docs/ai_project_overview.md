<!--
  ai_project_overview.md
  ──────────────────────
  This file is read by the MCP server tool `get_project_overview` and served
  to AI coding assistants (GitHub Copilot, Cursor, Claude Code, Windsurf …)
  so they understand the project BEFORE generating or reviewing code.

  HOW TO USE THIS TEMPLATE
  ─────────────────────────
  1. Copy this file to <your-django-project>/docs/ai_project_overview.md
  2. Fill in every section marked  ← CUSTOMIZE
  3. Delete anything that does not apply to your project
  4. Keep it honest — AI tools use this as ground truth

  Commit this file to version control so the whole team benefits.
-->

# AI Project Overview

> **Project:** <!-- ← CUSTOMIZE: your project name -->
> **Stack:** Django · Django REST Framework · PostgreSQL
> **Architecture:** Service-Layer (Model → Repository → Service → View)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Layer Responsibilities](#2-layer-responsibilities)
3. [Directory Structure](#3-directory-structure)
4. [Coding Rules](#4-coding-rules)
5. [Import Order](#5-import-order)
6. [Model Conventions](#6-model-conventions)
7. [API Response Conventions](#7-api-response-conventions)
8. [Queryset Optimization](#8-queryset-optimization)
9. [Error Handling](#9-error-handling)
10. [Testing Conventions](#10-testing-conventions)
11. [Migration Policy](#11-migration-policy)
12. [Environment Variables](#12-environment-variables)
13. [Key Design Decisions](#13-key-design-decisions)
14. [Apps in This Project](#14-apps-in-this-project)

---

## 1. Architecture Overview

Every HTTP request flows through exactly these layers — no shortcuts:

```
HTTP Request
    │
    ▼
View          HTTP surface only — parse input, call service, return Response
    │
    ▼
Service       All business logic, validation, transactions
    │
    ▼
Repository    All ORM / queryset access — no logic here
    │
    ▼
Model         Schema, DB constraints, domain properties
```

**Non-negotiable rules:**
- Views **never** access the ORM directly
- Services **never** return `Response` objects
- Repositories **never** contain business logic
- Serializers **never** contain business logic — validate input and shape output only

---

## 2. Layer Responsibilities

| Layer | Location | Single Responsibility |
|-------|----------|-----------------------|
| **Model** | `apps/<app>/models.py` | Schema, DB constraints, `__str__`, computed properties |
| **Repository** | `apps/<app>/repositories.py` | All ORM access; select/prefetch, filters, bulk ops |
| **Service** | `apps/<app>/services.py` | Business rules, orchestration, `@transaction.atomic` |
| **Serializer** | `apps/<app>/api/v1/serializers.py` | Input validation + output shaping (no DB, no logic) |
| **View** | `apps/<app>/api/v1/views.py` | Parse HTTP → call service → return `Response` |
| **URLs** | `apps/<app>/api/v1/urls.py` | Route registration only |
| **Constants** | `apps/<app>/constants.py` | `TextChoices`, `IntegerChoices`, static lookup tables |
| **Admin** | `apps/<app>/admin.py` | Django admin registration |
| **Signals** | `apps/<app>/signals.py` | Decoupled side-effects (use sparingly) |

---

## 3. Directory Structure

```
<project_root>/                      ← PROJECT_ROOT env var points here
├── apps/
│   └── <app_name>/                  ← one directory per domain
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py
│       ├── repositories.py
│       ├── services.py
│       ├── constants.py
│       ├── admin.py
│       ├── signals.py               (optional)
│       ├── tasks.py                 (optional — Celery)
│       ├── migrations/
│       │   └── 0001_initial.py
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── test_models.py
│       │   ├── test_services.py
│       │   └── test_views.py
│       └── api/
│           └── v1/
│               ├── __init__.py
│               ├── serializers.py
│               ├── views.py
│               └── urls.py
│
├── config/
│   ├── __init__.py
│   ├── urls.py                      ← root URL config
│   ├── wsgi.py
│   ├── asgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py                  ← shared settings
│       ├── development.py
│       ├── staging.py
│       └── production.py
│
├── docs/
│   └── ai_project_overview.md      ← this file
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── manage.py
└── .env.example
```

---

## 4. Coding Rules

### Rule 1 — Views delegate to services; no ORM in views

```python
# ✅ Correct — view is thin
class InvoiceView(BaseApiView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = InvoiceService()

    def post(self, request):
        serializer = InvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = self.service.create_invoice(serializer.validated_data)
        return Response(
            {"success": True, "data": InvoiceSerializer(invoice).data},
            status=status.HTTP_201_CREATED,
        )

# ❌ Wrong — business logic and ORM leaking into the view
class InvoiceView(BaseApiView):
    def post(self, request):
        if request.data.get("amount", 0) <= 0:       # ← belongs in service
            return Response({"error": "..."}, status=400)
        invoice = Invoice.objects.create(**request.data)  # ← belongs in repository
        send_invoice_email(invoice)                   # ← belongs in service
        return Response(...)
```

### Rule 2 — Services own all business logic and transactions

```python
# ✅ Correct
class InvoiceService(BaseService):
    def __init__(self):
        self.repo = InvoiceRepository()

    @transaction.atomic
    def create_invoice(self, data: dict) -> Invoice:
        self._validate_amount(data["amount"])
        invoice = self.repo.create(**data)
        self.repo.create_audit_log(invoice, action="created")   # same transaction
        return invoice

    def _validate_amount(self, amount) -> None:
        if amount <= 0:
            raise ServiceError("Invoice amount must be positive.")
```

### Rule 3 — Repositories own all ORM access

```python
# ✅ Correct
class InvoiceRepository(BaseRepository):
    model = Invoice

    def get_pending_for_user(self, user_id: int):
        return (
            self.model.objects
            .filter(user_id=user_id, status=InvoiceStatus.PENDING, is_deleted=False)
            .select_related("user", "subscription")
            .prefetch_related("line_items")
            .order_by("-created_at")
        )

# ❌ Wrong — queryset leaking into a service
class InvoiceService(BaseService):
    def get_pending(self, user_id):
        return Invoice.objects.filter(user_id=user_id)  # ← belongs in repository
```

### Rule 4 — Serializers validate format and shape output only

```python
# ✅ Correct
class InvoiceSerializer(BaseModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "amount", "status", "due_date", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

# ❌ Wrong — DB access inside serializer
class InvoiceSerializer(BaseModelSerializer):
    def validate(self, data):
        if Invoice.objects.filter(...).exists():  # ← belongs in service
            raise serializers.ValidationError(...)
        return data
```

---

## 5. Import Order

Always use this exact sequence, with a blank line between each group:

```python
# 1. Python standard library
import os
import json
from decimal import Decimal
from typing import Optional, List

# 2. Django core
from django.db import models, transaction
from django.db.models import Q, Sum
from django.conf import settings
from django.utils import timezone

# 3. Third-party packages
from rest_framework import serializers, status
from rest_framework.response import Response

# 4. Internal shared / base classes  ← CUSTOMIZE package names for your project
from common.base.base_model import BaseModel
from common.base.base_repository import BaseRepository, RepositoryError
from common.base.base_service import BaseService, ServiceError
from common.base.base_api_view import BaseApiView
from common.base.base_serializer import BaseModelSerializer

# 5. Local app imports  (models → repositories → services → serializers → constants)
from apps.<app>.models import MyModel
from apps.<app>.repositories import MyRepository
from apps.<app>.services import MyService
from apps.<app>.api.v1.serializers import MySerializer
from apps.<app>.constants import MyStatus
```

---

## 6. Model Conventions

```python
from common.base.base_model import BaseModel  # ← CUSTOMIZE base class name


class Invoice(BaseModel):
    """
    BaseModel provides: id (UUID PK), created_at, updated_at, is_deleted (soft delete).
    Define domain fields below.
    """
    user     = models.ForeignKey(
        "users.User", on_delete=models.PROTECT, related_name="invoices"
    )
    amount   = models.DecimalField(max_digits=10, decimal_places=2)
    status   = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.PENDING
    )
    due_date = models.DateField()

    class Meta:
        db_table            = "billing_invoice"   # always explicit
        verbose_name        = "Invoice"
        verbose_name_plural = "Invoices"
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self) -> str:
        return f"Invoice #{self.pk} — {self.user_id}"

    # ── Domain properties (read-only computed values only) ─────────────────

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone
        return (
            self.due_date < timezone.now().date()
            and self.status == InvoiceStatus.PENDING
        )
```

**Model checklist:**
- [ ] Inherits from `BaseModel`
- [ ] `db_table` is explicit and follows `<app>_<model>` convention
- [ ] `__str__` defined
- [ ] `class Meta` with `verbose_name` and `ordering`
- [ ] FK fields use `on_delete=models.PROTECT` unless cascade is intentional
- [ ] Status fields use `TextChoices` / `IntegerChoices` from `constants.py`
- [ ] DB indexes on filtered/ordered fields

---

## 7. API Response Conventions

**Success (single object):**
```json
{
  "success": true,
  "data": { "id": "abc-123", "amount": "100.00" },
  "message": "Invoice created successfully.",
  "errors": null
}
```

**Success (list, paginated):**
```json
{
  "success": true,
  "data": {
    "count": 42,
    "next": "https://api.example.com/invoices/?page=2",
    "previous": null,
    "results": [ ... ]
  },
  "message": null,
  "errors": null
}
```

**Validation error — 400:**
```json
{
  "success": false,
  "data": null,
  "message": "Validation failed.",
  "errors": { "amount": ["This field is required."] }
}
```

**Not found — 404:**
```json
{
  "success": false,
  "data": null,
  "message": "Invoice not found.",
  "errors": null
}
```

**Business rule violation — 422:**
```json
{
  "success": false,
  "data": null,
  "message": "Only pending invoices can be cancelled.",
  "errors": null
}
```

HTTP status codes in use: `200`, `201`, `204`, `400`, `401`, `403`, `404`, `409`, `422`, `500`

---

## 8. Queryset Optimization

| Situation | Method | SQL effect |
|-----------|--------|-----------|
| Access FK / OneToOne field | `.select_related("field")` | JOIN in single query |
| Access M2M / reverse FK | `.prefetch_related("field")` | Separate query, Python join |
| Need only some columns | `.only("f1", "f2")` | SELECT specific columns |
| Count rows | `.count()` | `SELECT COUNT(*)` |
| Check existence | `.exists()` | `SELECT 1 LIMIT 1` |

**Anti-patterns:**

```python
# ❌ N+1 — DB hit inside a loop
for order in Order.objects.all():
    print(order.user.email)              # 1 extra query per order

# ✅ Fix
for order in Order.objects.select_related("user"):
    print(order.user.email)              # 0 extra queries

# ❌ Loading all rows to count
total = len(Invoice.objects.filter(status="pending"))

# ✅ Fix
total = Invoice.objects.filter(status="pending").count()

# ❌ Boolean check loads all rows
if Invoice.objects.filter(user=user):
    ...

# ✅ Fix
if Invoice.objects.filter(user=user).exists():
    ...

# ❌ Bulk inserts in a loop — N queries
for item in items:
    MyModel.objects.create(**item)

# ✅ Fix — 1 query
MyModel.objects.bulk_create([MyModel(**item) for item in items])
```

---

## 9. Error Handling

```python
# services.py
class InvoiceService(BaseService):

    def get_invoice(self, pk) -> Invoice:
        obj = self.repo.get_by_id(pk)
        if obj is None:
            raise ServiceError("Invoice not found.", code="not_found")
        return obj

    def cancel_invoice(self, pk) -> Invoice:
        invoice = self.get_invoice(pk)
        if invoice.status != InvoiceStatus.PENDING:
            raise ServiceError(
                "Only pending invoices can be cancelled.",
                code="invalid_state",
            )
        return self.repo.update(invoice, status=InvoiceStatus.CANCELLED)
```

`BaseApiView` automatically converts `ServiceError` to the correct HTTP response.

**Error code → HTTP status mapping:**

| `code` | HTTP | When to use |
|--------|------|-------------|
| `not_found` | 404 | Resource doesn't exist |
| `invalid_state` | 422 | Business rule violation |
| `permission_denied` | 403 | Missing access rights |
| `conflict` | 409 | Duplicate / concurrency issue |
| `validation_failed` | 400 | Input validation (usually from serializer) |

---

## 10. Testing Conventions

```python
# tests/test_services.py
from django.test import TestCase
from unittest.mock import MagicMock, patch

from apps.billing.services import InvoiceService
from common.base.base_service import ServiceError


class TestInvoiceService(TestCase):

    def setUp(self):
        self.service = InvoiceService()

    def test_create_invoice_success(self):
        data = {"user_id": 1, "amount": "100.00", "due_date": "2026-12-31"}
        invoice = self.service.create_invoice(data)
        self.assertEqual(str(invoice.amount), "100.00")

    def test_create_invoice_rejects_zero_amount(self):
        with self.assertRaises(ServiceError):
            self.service.create_invoice({"amount": "0.00", "user_id": 1, "due_date": "2026-12-31"})

    def test_cancel_non_pending_invoice_raises(self):
        invoice = MagicMock(status="paid")
        self.service.repo.get_by_id = MagicMock(return_value=invoice)
        with self.assertRaises(ServiceError):
            self.service.cancel_invoice(pk=1)
```

**Test file responsibilities:**

| File | What to test |
|------|-------------|
| `test_models.py` | `__str__`, properties, clean/save hooks |
| `test_repositories.py` | ORM queries (use `TestCase` for real DB) |
| `test_services.py` | Business rules (mock repositories) |
| `test_views.py` | API endpoints, HTTP status codes (use `APITestCase`) |

```bash
# Run tests
python manage.py test apps.<app>.tests
pytest apps/<app>/tests/ -v --tb=short
```

---

## 11. Migration Policy

- Every model change **requires** a new migration
- Migration files are **committed to version control** — never gitignore them
- **Never edit** a migration that has been applied to any environment — create a new one
- Name non-trivial migrations: `makemigrations --name add_invoice_due_date`
- Squash old apps periodically to keep history manageable

**Before every deployment:**
```bash
python manage.py migrate --check     # exits non-zero if unapplied migrations exist
python manage.py showmigrations      # lists all migrations and their applied state
```

**Large-table migration checklist:**
- [ ] Add indexes in a separate migration after adding columns
- [ ] Use `RunSQL(..., "CREATE INDEX CONCURRENTLY ...")` on PostgreSQL
- [ ] Test migration time against a production-scale data snapshot

---

## 12. Environment Variables

<!-- ← CUSTOMIZE: update with your actual variables -->

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `DJANGO_SETTINGS_MODULE` | ✅ | `config.settings.development` | Active settings module |
| `PROJECT_ROOT` | ✅ | `/home/user/myproject` | Used by MCP server to locate project |
| `SECRET_KEY` | ✅ | `django-insecure-xxx` | Django secret key — never commit real value |
| `DATABASE_URL` | ✅ | `postgresql://user:pass@localhost/db` | PostgreSQL DSN |
| `DEBUG` | ✅ | `True` / `False` | Enable debug mode |
| `ALLOWED_HOSTS` | ✅ | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `REDIS_URL` | ⬜ | `redis://localhost:6379/0` | Cache + Celery broker |
| `CELERY_BROKER_URL` | ⬜ | `redis://localhost:6379/1` | Celery task queue |
| `SENTRY_DSN` | ⬜ | `https://...@sentry.io/xxx` | Error tracking |

```bash
cp .env.example .env   # then fill in the values
```

---

## 13. Key Design Decisions

<!-- ← CUSTOMIZE: document the important decisions made for THIS project.
     Each entry should state the decision and the reason why.
     AI tools use this section to understand WHY code is written a certain way. -->

1. **Service-layer architecture**
   Business logic lives in services only — not in views, serializers, or models.
   Services are independently unit-testable and decoupled from HTTP.

2. **Repository pattern**
   All `Model.objects.*` calls are centralised in repositories.
   Optimisations (`select_related`, indexes) have a single place to live.

3. **Soft delete everywhere**
   `BaseModel` provides `is_deleted`. Nothing is hard-deleted from production.
   Repositories automatically filter `is_deleted=False` on all queries.

4. **Atomic service methods**
   Every service method that writes to the DB uses `@transaction.atomic`.
   Partial writes are automatically rolled back on any exception.

5. **API versioning via URL path**
   All endpoints live under `/api/v1/`. Breaking changes get a new `/api/v2/`
   namespace — never in-place changes to existing versioned routes.

6. **No raw SQL**
   All DB access uses the Django ORM. Raw SQL is allowed only inside
   data migrations via `RunSQL`.

7. **No business logic in serializers**
   Serializers handle format/type validation (DRF built-ins).
   Domain rules (uniqueness per business logic, state transitions) live in services.

<!-- ← CUSTOMIZE: add more decisions specific to your project -->

---

## 14. Apps in This Project

<!-- ← CUSTOMIZE: list the Django apps and what each one does.
     This is the most important section for AI context — fill it in completely.

     Example:
     | App | Domain | Key Models |
     |-----|--------|------------|
     | `users` | User accounts, authentication, profiles | `User`, `UserProfile` |
     | `billing` | Subscriptions, invoices, payments | `Subscription`, `Invoice`, `Payment` |
     | `notifications` | Email / push dispatching | `Notification`, `NotificationTemplate` |
     | `audit` | Immutable audit log | `AuditLog` |
-->

| App | Domain | Key Models |
|-----|--------|------------|
| _(add your apps here)_ | | |

---

*This file is read by the MCP `get_project_overview` tool and served to AI assistants.
Keep it up to date — it is the AI's source of truth for this codebase.*
