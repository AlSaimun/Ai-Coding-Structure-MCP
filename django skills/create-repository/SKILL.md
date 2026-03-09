---
name: create-repository
description: Create a Django repository class following the project coding structure. Use this skill when the user asks to create a repository, add a repository layer, or wire a model to its repository. Enforces BaseRepository inheritance and single-responsibility ORM encapsulation.
argument-hint: <AppName> <ModelName>
---

# Create Repository Skill

## What This Skill Does
Creates a repository class that wraps a Django model and exposes it through `BaseRepository`. This is the **only** layer allowed to interact with the ORM directly.

## Rules to Follow
- **Always** inherit from `BaseRepository`
- **Always** call `super().__init__(ModelClass)` in `__init__`
- **Only** raw ORM queries go in the repository — no business logic
- **Never** put filtering, pagination, or business rules here
- **Never** access `Model.objects` anywhere except inside repository methods

## Import Order (Strictly)
```python
# Group 3 — dxh packages
from dxh_common.base.base_repository import BaseRepository

# Group 4 — Local app
from apps.myapp.models import MyModel
```

## Template
```python
from dxh_common.base.base_repository import BaseRepository

from apps.myapp.models import MyModel


class MyModelRepository(BaseRepository):
    def __init__(self):
        super().__init__(MyModel)
```

## File Location
`apps/<app_name>/repositories/<model_name_snake_case>_repository.py`

## After Creating
Add the export to `apps/<app_name>/repositories/__init__.py`:
```python
from apps.myapp.repositories.my_model_repository import MyModelRepository
```

## Custom ORM Methods (When Needed)
Only add custom methods here if `BaseRepository` methods are insufficient:
```python
class MyModelRepository(BaseRepository):
    def __init__(self):
        super().__init__(MyModel)

    def get_by_slug(self, slug):
        return self.model.objects.filter(slug=slug).first()
```
