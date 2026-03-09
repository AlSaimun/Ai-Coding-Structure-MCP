---
name: create-service
description: Create a Django service class following the project coding structure. Use this skill when the user asks to create a service, add business logic, add a filter method, or wire a repository to business operations. Enforces BaseService, RepositoryError→ServiceError, conditional filter pattern, and dict logger.
argument-hint: <AppName> <ModelName> [filter fields]
---

# Create Service Skill

## What This Skill Does
Creates a service class that contains all business logic, delegates data access to the repository, and follows the canonical filter pattern used throughout this project.

## Rules to Follow
- **Always** inherit from `BaseService`
- **Always** call `super().__init__(MyModelRepository())` in `__init__`
- **Always** use `self.get(...)`, `self.get_all()`, `self.create(...)`, `self.update(...)`, `self.delete(...)` — **never** `Model.objects`
- **Always** wrap every method in `try/except RepositoryError as e: raise ServiceError(...)`
- **Always** use module-level logger: `logger = Logger(__name__)`
- **Always** use dict logger format: `logger.error({"event": "ClassName:method", "error": str(e)})`
- **Never** put `Model.objects` calls directly in the service

## Import Order (Strictly)
```python
# Group 2 — Django
from django.db.models import Q

# Group 3 — dxh packages
from dxh_common.logger import Logger
from dxh_common.base.base_repository import RepositoryError
from dxh_common.base.base_service import BaseService, ServiceError

# Group 4 — Local app
from apps.myapp.repositories import MyModelRepository
```

## Filter Pattern (Canonical — Copy Exactly)
```python
def get_items(self, **filters):
    try:
        items = self.get_all().select_related("foreignkey_field").prefetch_related("many_to_many_field")
        items = items.order_by(filters.get("ordering", "-created_at"))

        if "search" in filters:
            items = items.filter(
                Q(name__icontains=filters["search"]) |
                Q(description__icontains=filters["search"])
            )

        if "name" in filters:
            items = items.filter(name__icontains=filters["name"])

        if "status" in filters:
            items = items.filter(status=filters["status"])

        return items

    except RepositoryError as e:
        raise ServiceError(f"Service error during get operation: {e}")
```

## Full Template
```python
from django.db.models import Q

from dxh_common.logger import Logger
from dxh_common.base.base_repository import RepositoryError
from dxh_common.base.base_service import BaseService, ServiceError

from apps.myapp.repositories import MyModelRepository

logger = Logger(__name__)


class MyModelService(BaseService):
    def __init__(self):
        super().__init__(MyModelRepository())

    def get_items(self, **filters):
        try:
            items = self.get_all().select_related("foreignkey_field").prefetch_related("many_to_many_field")
            items = items.order_by(filters.get("ordering", "-created_at"))

            if "search" in filters:
                items = items.filter(
                    Q(name__icontains=filters["search"]) |
                    Q(description__icontains=filters["search"])
                )

            if "name" in filters:
                items = items.filter(name__icontains=filters["name"])

            if "status" in filters:
                items = items.filter(status=filters["status"])

            return items

        except RepositoryError as e:
            raise ServiceError(f"Service error during get operation: {e}")
```

## File Location
`apps/<app_name>/services/<model_name_snake_case>_service.py`

## After Creating
Add the export to `apps/<app_name>/services/__init__.py`:
```python
from apps.myapp.services.my_model_service import MyModelService
```

## Circular Import Warning
If adding `SubscriptionService` or another service that causes a circular import, use lazy import in `__init__`:
```python
def __init__(self):
    super().__init__(MyModelRepository())
    # Lazy import to avoid circular dependency
    from apps.subscription.services.subscription_service import SubscriptionService
    self.subscription_service = SubscriptionService()
```
