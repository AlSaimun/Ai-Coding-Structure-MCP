---
name: create-view
description: Create a DRF API view following the project coding structure. Use this skill when the user asks to create a view, add an API endpoint, create a CRUD API, or add GET/POST/PUT/DELETE handlers. Enforces BaseApiView, services in __init__, empty query param stripping, dict logger, and standard response shape.
argument-hint: <AppName> <ModelName> [HTTP methods: GET POST PUT DELETE]
---

# Create View Skill

## What This Skill Does
Creates a complete DRF API view class with all requested HTTP methods, following the project's strict response shape and error handling conventions.

## Rules to Follow
- **Always** inherit from `BaseApiView`
- **Always** instantiate services in `__init__`: `self.my_service = MyService()`
- **Always** instantiate pagination in `__init__`: `self.pagination_class = CustomPagination()`
- **Always** strip empty query params before passing to service: `{key: value for key, value in request.query_params.items() if value}`
- **Always** wrap every method in `try/except Exception as e: logger.error({...}); raise e`
- **Always** use `status.HTTP_*` constants — **never** raw integers
- **Never** call `Model.objects` directly — always go through the service
- **Never** instantiate services outside `__init__`

## Import Order (Strictly)
```python
# Group 3 — dxh packages
from dxh_libraries.translation import gettext_lazy as _
from dxh_common.logger import Logger
from dxh_common.base.base_view import BaseApiView

# Group 2 — DRF (DRF goes in group 2, dxh in group 3)
from rest_framework import status
from rest_framework.response import Response

# Group 4 — Local app
from apps.core.api.v1.pagination import CustomPagination
from apps.myapp.api.v1.serializers import MyModelSerializer
from apps.myapp.services import MyModelService
```

Note: Correct group 2 vs group 3 — DRF (`rest_framework`) is group 2, `dxh_*` is group 3.

## Response Shape (All Responses Must Follow This)
```python
# List
{"message": _("..."), "data": [...], "pagination": {...}}

# Single object
{"message": _("..."), "data": {...}}

# Error
{"message": _("..."), "errors": {...}}

# Delete success
{"message": _("...")}
```

## Full CRUD Template
```python
from dxh_libraries.translation import gettext_lazy as _

from dxh_common.logger import Logger
from dxh_common.base.base_view import BaseApiView
from rest_framework import status
from rest_framework.response import Response

from apps.core.api.v1.pagination import CustomPagination
from apps.myapp.api.v1.serializers import MyModelSerializer
from apps.myapp.services import MyModelService

logger = Logger(__name__)


class MyModelAPIView(BaseApiView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.my_model_service = MyModelService()
        self.pagination_class = CustomPagination()

    def get(self, request, id=None):
        try:
            if id:
                item = self.my_model_service.get(id=id)
                if not item:
                    return Response({"message": _("Not found")}, status=status.HTTP_400_BAD_REQUEST)
                serializer = MyModelSerializer(item)
                return Response(
                    {"message": _("Retrieved successfully"), "data": serializer.data},
                    status=status.HTTP_200_OK,
                )

            query_params = {key: value for key, value in request.query_params.items() if value}
            items = self.my_model_service.get_items(**query_params)
            paginated_data = self.pagination_class.paginate_queryset(items, request)
            serializer = MyModelSerializer(paginated_data, many=True)
            paginated_response = self.pagination_class.get_paginated_response(serializer.data)
            return Response(
                {
                    "message": _("Retrieved successfully"),
                    "data": paginated_response.data["records"],
                    "pagination": paginated_response.data["pagination"],
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error({"event": "MyModelAPIView:get", "error": str(e)})
            raise e

    def post(self, request):
        try:
            serializer = MyModelSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"message": _("Invalid data"), "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item = self.my_model_service.create(**serializer.validated_data)
            return Response(
                {"message": _("Created successfully"), "data": MyModelSerializer(item).data},
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            logger.error({"event": "MyModelAPIView:post", "error": str(e)})
            raise e

    def put(self, request, id):
        try:
            item = self.my_model_service.get(id=id)
            if not item:
                return Response({"message": _("Not found")}, status=status.HTTP_400_BAD_REQUEST)
            serializer = MyModelSerializer(item, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {"message": _("Invalid data"), "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            updated = self.my_model_service.update(item, **serializer.validated_data)
            return Response(
                {"message": _("Updated successfully"), "data": MyModelSerializer(updated).data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error({"event": "MyModelAPIView:put", "error": str(e), "id": id})
            raise e

    def delete(self, request, id):
        try:
            item = self.my_model_service.get(id=id)
            if not item:
                return Response({"message": _("Not found")}, status=status.HTTP_400_BAD_REQUEST)
            self.my_model_service.delete(item)
            return Response({"message": _("Deleted successfully")}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error({"event": "MyModelAPIView:delete", "error": str(e), "id": id})
            raise e
```

## File Location
`apps/<app_name>/api/v1/views/<model_name_snake_case>_view.py`

## After Creating
1. Add the export to `apps/<app_name>/api/v1/views/__init__.py`
2. Add URLs to `apps/<app_name>/api/v1/urls.py`:
```python
path("items/", views.MyModelAPIView.as_view(), name="item-list"),
path("items/<int:id>/", views.MyModelAPIView.as_view(), name="item-detail"),
```
