---
name: create-feature
description: Create a complete end-to-end Django REST Framework feature including model, repository, service, serializer, view, and URL registration. Use this skill when the user asks to create a full feature, a new API, or a complete CRUD for a new entity. Always creates all 6 layers in the correct order and wires them together.
argument-hint: <AppName> <ModelName> [field descriptions] [special business rules]
---

# Create Feature Skill

## What This Skill Does
Scaffolds a complete feature across all 6 layers in the correct order:
1. **Model** → 2. **Repository** → 3. **Service** → 4. **Serializer** → 5. **View** → 6. **URLs**

Plus updates all `__init__.py` files and reminds the user to create migrations.

## Layer Order (Always Follow)
```
URL  ──►  View  ──►  Service  ──►  Repository  ──►  Model
```
Never skip, never reorder.

## Step 1: Model (`apps/<app>/models/<name>.py`)
- Inherit `BaseModel`
- Set `db_table = "appname_modelnames"`
- All labels use `_("...")`
- Implement `__str__`

## Step 2: Repository (`apps/<app>/repositories/<name>_repository.py`)
- Inherit `BaseRepository`
- `super().__init__(ModelClass)`
- No business logic here

## Step 3: Service (`apps/<app>/services/<name>_service.py`)
- Inherit `BaseService`, `super().__init__(NameRepository())`
- Implement `get_<plural>(**filters)` with conditional filter pattern
- All methods: `try/except RepositoryError as e: raise ServiceError(...)`
- `logger = Logger(__name__)` at module level

## Step 4: Serializer (`apps/<app>/api/v1/serializers/<name>_serializer.py`)
- Inherit `serializers.ModelSerializer`
- Explicit `fields` list — never `"__all__"`
- Nested serializers prefixed with `_`

## Step 5: View (`apps/<app>/api/v1/views/<name>_view.py`)
- Inherit `BaseApiView`
- Services and pagination in `__init__`
- Strip empty query params
- All methods: `try/except Exception as e: logger.error({...}); raise e`
- Response shape: `{"message": _("..."), "data": ..., "pagination": ...}`

## Step 6: URLs (`apps/<app>/api/v1/urls.py`)
```python
path("<plural>/", views.MyModelAPIView.as_view(), name="<name>-list"),
path("<plural>/<int:id>/", views.MyModelAPIView.as_view(), name="<name>-detail"),
```

## __init__.py Updates (All 4 Required)
```python
# apps/<app>/models/__init__.py
from apps.myapp.models.my_model import MyModel

# apps/<app>/repositories/__init__.py
from apps.myapp.repositories.my_model_repository import MyModelRepository

# apps/<app>/services/__init__.py
from apps.myapp.services.my_model_service import MyModelService

# apps/<app>/api/v1/serializers/__init__.py
from apps.myapp.api.v1.serializers.my_model_serializer import MyModelSerializer

# apps/<app>/api/v1/views/__init__.py
from apps.myapp.api.v1.views.my_model_view import MyModelAPIView
```

## After Generating All Files
Remind the user to run:
```bash
python manage.py makemigrations <app_name>
python manage.py migrate
```

## Full Example Output (Tag in core app)

### `apps/core/models/tag.py`
```python
from django.db import models

from dxh_common.base.base_model import BaseModel
from dxh_libraries.translation import gettext_lazy as _


class Tag(BaseModel):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Name"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = "core_tags"
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.name
```

### `apps/core/repositories/tag_repository.py`
```python
from dxh_common.base.base_repository import BaseRepository

from apps.core.models import Tag


class TagRepository(BaseRepository):
    def __init__(self):
        super().__init__(Tag)
```

### `apps/core/services/tag_service.py`
```python
from django.db.models import Q

from dxh_common.logger import Logger
from dxh_common.base.base_repository import RepositoryError
from dxh_common.base.base_service import BaseService, ServiceError

from apps.core.repositories import TagRepository

logger = Logger(__name__)


class TagService(BaseService):
    def __init__(self):
        super().__init__(TagRepository())

    def get_tags(self, **filters):
        try:
            tags = self.get_all()
            tags = tags.order_by(filters.get("ordering", "name"))

            if "search" in filters:
                tags = tags.filter(
                    Q(name__icontains=filters["search"]) |
                    Q(description__icontains=filters["search"])
                )

            if "name" in filters:
                tags = tags.filter(name__icontains=filters["name"])

            return tags

        except RepositoryError as e:
            raise ServiceError(f"Service error during get operation: {e}")
```

### `apps/core/api/v1/serializers/tag_serializer.py`
```python
from rest_framework import serializers

from apps.core.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "description", "created_at", "updated_at"]
```

### `apps/core/api/v1/views/tag_view.py`
```python
from dxh_libraries.translation import gettext_lazy as _

from dxh_common.logger import Logger
from dxh_common.base.base_view import BaseApiView
from rest_framework import status
from rest_framework.response import Response

from apps.core.api.v1.pagination import CustomPagination
from apps.core.api.v1.serializers import TagSerializer
from apps.core.services import TagService

logger = Logger(__name__)


class TagAPIView(BaseApiView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tag_service = TagService()
        self.pagination_class = CustomPagination()

    def get(self, request, id=None):
        try:
            if id:
                tag = self.tag_service.get(id=id)
                if not tag:
                    return Response({"message": _("Tag not found")}, status=status.HTTP_400_BAD_REQUEST)
                return Response(
                    {"message": _("Tag retrieved successfully"), "data": TagSerializer(tag).data},
                    status=status.HTTP_200_OK,
                )

            query_params = {key: value for key, value in request.query_params.items() if value}
            tags = self.tag_service.get_tags(**query_params)
            paginated_data = self.pagination_class.paginate_queryset(tags, request)
            serializer = TagSerializer(paginated_data, many=True)
            paginated_response = self.pagination_class.get_paginated_response(serializer.data)
            return Response(
                {
                    "message": _("Tags retrieved successfully"),
                    "data": paginated_response.data["records"],
                    "pagination": paginated_response.data["pagination"],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error({"event": "TagAPIView:get", "error": str(e)})
            raise e

    def post(self, request):
        try:
            serializer = TagSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"message": _("Invalid data"), "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            tag = self.tag_service.create(**serializer.validated_data)
            return Response(
                {"message": _("Tag created successfully"), "data": TagSerializer(tag).data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error({"event": "TagAPIView:post", "error": str(e)})
            raise e

    def put(self, request, id):
        try:
            tag = self.tag_service.get(id=id)
            if not tag:
                return Response({"message": _("Tag not found")}, status=status.HTTP_400_BAD_REQUEST)
            serializer = TagSerializer(tag, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {"message": _("Invalid data"), "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            updated = self.tag_service.update(tag, **serializer.validated_data)
            return Response(
                {"message": _("Tag updated successfully"), "data": TagSerializer(updated).data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error({"event": "TagAPIView:put", "error": str(e), "id": id})
            raise e

    def delete(self, request, id):
        try:
            tag = self.tag_service.get(id=id)
            if not tag:
                return Response({"message": _("Tag not found")}, status=status.HTTP_400_BAD_REQUEST)
            self.tag_service.delete(tag)
            return Response({"message": _("Tag deleted successfully")}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error({"event": "TagAPIView:delete", "error": str(e), "id": id})
            raise e
```

### URL additions to `apps/core/api/v1/urls.py`
```python
path("tags/", views.TagAPIView.as_view(), name="tag-list"),
path("tags/<int:id>/", views.TagAPIView.as_view(), name="tag-detail"),
```
