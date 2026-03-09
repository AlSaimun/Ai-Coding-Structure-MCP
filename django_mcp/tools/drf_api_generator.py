"""
Tool: generate_drf_api

Given a model name and app name, generates a complete DRF API scaffold following
the project's service-layer architecture:

  - Model stub
  - Repository
  - Service class
  - DRF ModelSerializer
  - APIView (list + detail)
  - URL patterns
  - Constants stub

All code follows the project's BaseModel / BaseService / BaseRepository / BaseApiView
conventions from dxh_common as defined in ai_project_overview.md.
"""

from __future__ import annotations

import re
from typing import Any

from .base import PatternTool, ToolDefinition

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "model_name": {
            "type": "string",
            "description": "PascalCase model name, e.g. 'UserProfile' or 'PaymentMethod'.",
        },
        "app_name": {
            "type": "string",
            "description": "Django app name (snake_case), e.g. 'users' or 'payments'.",
        },
        "fields": {
            "type": "string",
            "description": (
                "Optional comma-separated list of field names to include in the model "
                "and serializer, e.g. 'name, email, status'. Defaults to placeholder fields."
            ),
        },
    },
    "required": ["model_name", "app_name"],
}

# ── Templates ─────────────────────────────────────────────────────────────────

_MODEL_TEMPLATE = '''\
# apps/{app_name}/models.py
from django.db import models
from dxh_common.base.base_model import BaseModel


class {ModelName}(BaseModel):
    """
    {ModelName} entity.
    Add fields below — BaseModel already provides:
      id (UUID), created_at, updated_at, is_deleted
    """
{fields_block}
    class Meta:
        db_table = "{app_name}_{model_name}"
        verbose_name = "{ModelName}"
        verbose_name_plural = "{ModelName}s"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{ModelName}({{self.pk}})"
'''

_CONSTANTS_TEMPLATE = '''\
# apps/{app_name}/constants.py
from django.db import models
from dxh_libraries.translation import gettext_lazy as _


class {ModelName}Status(models.TextChoices):
    ACTIVE   = "active",   _("Active")
    INACTIVE = "inactive", _("Inactive")
'''

_REPOSITORY_TEMPLATE = '''\
# apps/{app_name}/repositories.py
from dxh_common.base.base_repository import BaseRepository

from apps.{app_name}.models import {ModelName}


class {ModelName}Repository(BaseRepository):
    model = {ModelName}

    def get_active(self):
        return (
            self.model.objects
            .filter(is_deleted=False)
            .select_related()      # add FK fields here
            .prefetch_related()    # add M2M / reverse FK fields here
        )

    def get_by_id(self, pk):
        return (
            self.model.objects
            .filter(pk=pk, is_deleted=False)
            .select_related()
            .first()
        )
'''

_SERVICE_TEMPLATE = '''\
# apps/{app_name}/services.py
from dxh_common.base.base_service import BaseService, ServiceError
from django.db import transaction

from apps.{app_name}.models import {ModelName}
from apps.{app_name}.repositories import {ModelName}Repository


class {ModelName}Service(BaseService):

    def __init__(self) -> None:
        self.repo = {ModelName}Repository()

    def list_{model_name}s(self):
        return self.repo.get_active()

    def get_{model_name}(self, pk) -> {ModelName}:
        instance = self.repo.get_by_id(pk)
        if instance is None:
            raise ServiceError("{ModelName} not found.")
        return instance

    @transaction.atomic
    def create_{model_name}(self, data: dict) -> {ModelName}:
        self._validate(data)
        return self.repo.create(**data)

    @transaction.atomic
    def update_{model_name}(self, pk, data: dict) -> {ModelName}:
        instance = self.get_{model_name}(pk)
        return self.repo.update(instance, **data)

    @transaction.atomic
    def delete_{model_name}(self, pk) -> None:
        instance = self.get_{model_name}(pk)
        self.repo.soft_delete(instance)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _validate(self, data: dict) -> None:
        # Add domain-level validation here (raise ServiceError on failure)
        pass
'''

_SERIALIZER_TEMPLATE = '''\
# apps/{app_name}/api/v1/serializers.py
from dxh_common.base.base_serializer import BaseModelSerializer

from apps.{app_name}.models import {ModelName}


class {ModelName}Serializer(BaseModelSerializer):
    class Meta:
        model = {ModelName}
        fields = [
{serializer_fields}
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
'''

_VIEW_TEMPLATE = '''\
# apps/{app_name}/api/v1/views.py
from dxh_libraries.rest_framework import Response, status
from dxh_common.base.base_api_view import BaseApiView

from apps.{app_name}.services import {ModelName}Service
from apps.{app_name}.api.v1.serializers import {ModelName}Serializer


class {ModelName}ListView(BaseApiView):
    """GET /api/v1/{model_name}s/  — list all | POST — create"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = {ModelName}Service()

    def get(self, request):
        instances = self.service.list_{model_name}s()
        serializer = {ModelName}Serializer(instances, many=True)
        return Response({{"success": True, "data": serializer.data}})

    def post(self, request):
        serializer = {ModelName}Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.service.create_{model_name}(serializer.validated_data)
        out = {ModelName}Serializer(instance)
        return Response({{"success": True, "data": out.data}}, status=status.HTTP_201_CREATED)


class {ModelName}DetailView(BaseApiView):
    """GET /api/v1/{model_name}s/<pk>/  — retrieve | PATCH — update | DELETE — delete"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = {ModelName}Service()

    def get(self, request, pk):
        instance = self.service.get_{model_name}(pk)
        serializer = {ModelName}Serializer(instance)
        return Response({{"success": True, "data": serializer.data}})

    def patch(self, request, pk):
        serializer = {ModelName}Serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = self.service.update_{model_name}(pk, serializer.validated_data)
        out = {ModelName}Serializer(instance)
        return Response({{"success": True, "data": out.data}})

    def delete(self, request, pk):
        self.service.delete_{model_name}(pk)
        return Response({{"success": True, "message": "{ModelName} deleted."}}, status=status.HTTP_204_NO_CONTENT)
'''

_URLS_TEMPLATE = '''\
# apps/{app_name}/api/v1/urls.py
from django.urls import path

from apps.{app_name}.api.v1.views import {ModelName}ListView, {ModelName}DetailView

urlpatterns = [
    path("{model_name}s/",       {ModelName}ListView.as_view(),  name="{model_name}-list"),
    path("{model_name}s/<pk>/",  {ModelName}DetailView.as_view(), name="{model_name}-detail"),
]
'''


def _to_snake(pascal: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", pascal)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.lower()


def _build_fields_block(fields: list[str]) -> str:
    if not fields:
        return '    # name = models.CharField(max_length=255)\n    # status = models.CharField(max_length=50)\n'
    lines = []
    for f in fields:
        f = f.strip()
        if f:
            lines.append(f'    {f} = models.CharField(max_length=255)  # TODO: choose correct field type')
    return "\n".join(lines) + "\n"


def _build_serializer_fields(fields: list[str], model_name: str, snake: str) -> str:
    base = ["id", "created_at", "updated_at"]
    all_fields = base + [f.strip() for f in fields if f.strip()]
    if not fields:
        all_fields = base + ["# add your fields here"]
    return "\n".join(f'            "{f}",' for f in all_fields)


class GenerateDrfApiTool(PatternTool):
    """
    Generates a complete DRF API scaffold following the project's service-layer architecture.
    """

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="generate_drf_api",
            description=(
                "Given a model name and app name, generates a complete DRF API scaffold: "
                "Model, Repository, Service, Serializer, APIView (list + detail), URL patterns, "
                "and Constants. Follows service-layer architecture with BaseModel / BaseService / "
                "BaseRepository / BaseApiView conventions."
            ),
            input_schema=_SCHEMA,
        )

    def execute(self, arguments: dict[str, Any]) -> str:
        model_name: str = arguments.get("model_name", "MyModel").strip()
        app_name: str = arguments.get("app_name", "my_app").strip()
        fields_raw: str = arguments.get("fields", "")

        snake = _to_snake(model_name)
        fields = [f.strip() for f in fields_raw.split(",") if f.strip()] if fields_raw else []

        subs = {
            "{ModelName}": model_name,
            "{model_name}": snake,
            "{app_name}": app_name,
        }

        def render(template: str) -> str:
            for k, v in subs.items():
                template = template.replace(k, v)
            return template

        sections = [
            f"# DRF API Scaffold — `{model_name}` in app `{app_name}`",
            "",
            "## 1. Model",
            "```python",
            render(_MODEL_TEMPLATE).replace(
                "{fields_block}", _build_fields_block(fields)
            ),
            "```",
            "",
            "## 2. Constants",
            "```python",
            render(_CONSTANTS_TEMPLATE),
            "```",
            "",
            "## 3. Repository",
            "```python",
            render(_REPOSITORY_TEMPLATE),
            "```",
            "",
            "## 4. Service",
            "```python",
            render(_SERVICE_TEMPLATE),
            "```",
            "",
            "## 5. Serializer",
            "```python",
            render(_SERIALIZER_TEMPLATE).replace(
                "{serializer_fields}", _build_serializer_fields(fields, model_name, snake)
            ),
            "```",
            "",
            "## 6. Views",
            "```python",
            render(_VIEW_TEMPLATE),
            "```",
            "",
            "## 7. URL Patterns",
            "```python",
            render(_URLS_TEMPLATE),
            "```",
            "",
            "---",
            f"**Next steps:**",
            f"1. Add `apps.{app_name}` to `INSTALLED_APPS`",
            f"2. Register `apps.{app_name}.api.v1.urls` in `config/urls.py`",
            f"3. Run `python manage.py makemigrations {app_name}`",
            f"4. Run `python manage.py migrate`",
        ]
        return "\n".join(sections)
