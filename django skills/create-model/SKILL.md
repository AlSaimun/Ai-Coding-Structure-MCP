---
name: create-model
description: Create a Django model following the project coding structure. Use this skill when the user asks to create a model, add a model, or define a database table. Enforces BaseModel inheritance, db_table, verbose_name, gettext_lazy labels, and __str__.
argument-hint: <AppName> <ModelName> [field descriptions]
---

# Create Model Skill

## What This Skill Does
Creates a properly structured Django model in the correct app directory, following the project's strict coding conventions.

## Rules to Follow
- **Always** inherit from `BaseModel`, never `models.Model`
- **Always** set `db_table` in `Meta` using pattern `appname_modelnames` (plural, snake_case)
- **Always** use `verbose_name` and `verbose_name_plural` wrapped in `_("...")`
- **Always** implement `__str__` returning a meaningful string
- **Never** use bare `models.Model` as base class
- **Never** skip `db_table`
- **Never** use raw strings for labels — always `_("...")`

## Import Order (Strictly)
```python
# Group 2 — Django
from django.db import models

# Group 3 — dxh packages
from dxh_common.base.base_model import BaseModel
from dxh_libraries.translation import gettext_lazy as _
```
No Group 1 (stdlib) or Group 4 (local) needed for a basic model unless adding ForeignKey.

## Template
```python
from django.db import models

from dxh_common.base.base_model import BaseModel
from dxh_libraries.translation import gettext_lazy as _


class MyModel(BaseModel):
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = "app_my_models"
        verbose_name = _("My Model")
        verbose_name_plural = _("My Models")

    def __str__(self):
        return self.name
```

## File Location
`apps/<app_name>/models/<model_name_snake_case>.py`

## After Creating
1. Import the new model in `apps/<app_name>/models/__init__.py`

## ForeignKey Pattern
```python
company = models.ForeignKey(
    "core.Company",
    on_delete=models.CASCADE,
    related_name="my_models",
    verbose_name=_("Company"),
)
```
