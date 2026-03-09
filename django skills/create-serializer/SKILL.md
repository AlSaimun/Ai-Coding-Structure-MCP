---
name: create-serializer
description: Create a DRF serializer following the project coding structure. Use this skill when the user asks to create a serializer, add nested serializers, add computed fields, or wire a model to its API representation. Enforces private nested serializer prefix, SerializerMethodField for computed values, and getattr fallback for prefetch annotations.
argument-hint: <AppName> <ModelName> [fields to include]
---

# Create Serializer Skill

## What This Skill Does
Creates a DRF serializer with proper field definitions, nested object handling, and prefetch-safe annotations.

## Rules to Follow
- Private nested serializers **must** be prefixed with `_` (e.g., `_CompanySerializer`)
- Use `SerializerMethodField` for any computed or conditional field
- Use `getattr(obj, 'prefetch_attr', None)` with ORM fallback when reading prefetch annotations — **never** assume the prefetch is always present
- `read_only=True` on nested relation fields
- Fields list always explicitly defined — **never** use `fields = "__all__"`

## Import Order (Strictly)
```python
# Group 2 — DRF
from rest_framework import serializers

# Group 4 — Local app
from apps.myapp.models import MyModel
```

## Simple Serializer Template
```python
from rest_framework import serializers

from apps.myapp.models import MyModel


class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = ["id", "name", "description", "created_at", "updated_at"]
```

## Nested Serializer Template
```python
from rest_framework import serializers

from apps.myapp.models import MyModel
from apps.core.models import Company


class _CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "email"]


class MyModelSerializer(serializers.ModelSerializer):
    company = _CompanySerializer(read_only=True)
    computed_field = serializers.SerializerMethodField()

    class Meta:
        model = MyModel
        fields = ["id", "name", "company", "computed_field", "created_at", "updated_at"]

    def get_computed_field(self, obj):
        return obj.some_property
```

## Prefetch-Safe Pattern
When reading prefetched data that may or may not be present:
```python
def get_pricing_plans(self, obj):
    plans = getattr(obj, 'active_pricing_plans', None)
    if plans is None:
        plans = obj.pricing_plans.filter(is_active=True).order_by('price')
    return _PricingPlanSerializer(plans, many=True).data
```

## File Location
`apps/<app_name>/api/v1/serializers/<model_name_snake_case>_serializer.py`

## After Creating
Add the export to `apps/<app_name>/api/v1/serializers/__init__.py`:
```python
from apps.myapp.api.v1.serializers.my_model_serializer import MyModelSerializer
```
