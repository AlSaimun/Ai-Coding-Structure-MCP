---
name: fix-coding-structure
description: Audit and fix coding structure violations in Django files. Use this skill when a file breaks the project architecture rules — wrong import order, Model.objects in views/services, raw status integers, wrong logger format, missing __init__.py exports, wrong response shape, or missing BaseModel/BaseService/BaseRepository/BaseApiView inheritance.
argument-hint: file path or describe the violation
---

# Fix Coding Structure Skill

## What This Skill Does
Audits the provided file(s) against the project's coding rules and fixes every violation found. Always explains what was wrong and what was fixed.

## Violation Checklist — Check Every Item

### VIOLATION-1: Wrong Import Order
**Wrong:**
```python
from apps.core.models import Company       # local before dxh
from dxh_common.logger import Logger
```
**Fixed:**
```python
# Group 3 — dxh first
from dxh_common.logger import Logger

# Group 4 — local after
from apps.core.models import Company
```
**Rule:** stdlib → Django/DRF → dxh packages → local apps. Always blank-line-separated.

---

### VIOLATION-2: Model.objects in View or Service
**Wrong (in view or service):**
```python
agents = Agent.objects.filter(company=company)
```
**Fixed:**
- In a **view**: call the service method instead
- In a **service**: call `self.get_all().filter(...)` (BaseService method)
- `Model.objects` is only allowed inside a **repository**

---

### VIOLATION-3: Raw Integer Status Codes
**Wrong:**
```python
return Response(data, 200)
return Response(error, 400)
```
**Fixed:**
```python
return Response(data, status=status.HTTP_200_OK)
return Response(error, status=status.HTTP_400_BAD_REQUEST)
```

---

### VIOLATION-4: Wrong Logger Format
**Wrong:**
```python
logger.error(f"Error in get: {e}")
logger.error("Something failed")
logging.error(str(e))
```
**Fixed:**
```python
logger = Logger(__name__)  # module-level
logger.error({"event": "ClassName:method", "error": str(e)})
```

---

### VIOLATION-5: Wrong Response Shape
**Wrong:**
```python
return Response({"success": True, "result": data})
return Response(data)
```
**Fixed:**
```python
# List
return Response({"message": _("Retrieved successfully"), "data": records, "pagination": pagination}, status=status.HTTP_200_OK)
# Single object
return Response({"message": _("Retrieved successfully"), "data": serializer.data}, status=status.HTTP_200_OK)
# Error
return Response({"message": _("Invalid data"), "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
```

---

### VIOLATION-6: Wrong Base Class
**Wrong:**
```python
class MyModel(models.Model): ...       # should be BaseModel
class MyRepo(object): ...              # should be BaseRepository
class MyService: ...                   # should be BaseService
class MyView(APIView): ...             # should be BaseApiView
```
**Fixed:** Replace the base class with the correct one. Update imports accordingly.

---

### VIOLATION-7: Missing __init__.py Export
After creating any new class, check that the local `__init__.py` re-exports it:
```python
# repositories/__init__.py
from apps.myapp.repositories.my_model_repository import MyModelRepository
```
If missing, add it.

---

### VIOLATION-8: Services or Pagination Not in `__init__`
**Wrong (in view):**
```python
def get(self, request):
    service = MyService()   # instantiated inside method
```
**Fixed:**
```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.my_service = MyService()          # in __init__
    self.pagination_class = CustomPagination()
```

---

### VIOLATION-9: Empty Query Params Not Stripped
**Wrong:**
```python
items = self.service.get_items(**request.query_params)
```
**Fixed:**
```python
query_params = {key: value for key, value in request.query_params.items() if value}
items = self.service.get_items(**query_params)
```

---

### VIOLATION-10: company = plan.company (Business Rule)
**Wrong:**
```python
company = plan.company
```
**Fixed:**
```python
company = user.company  # every user owns their own company
```

---

## How to Use This Skill

1. Provide the file path or paste the code
2. This skill will check all 10 violation types
3. Each fix will be clearly labeled with which violation it addresses
4. All fixes are applied at once using the same coding structure

## Output Format
For each fix, output:
```
FIXED [VIOLATION-N]: <short description of what was wrong>
```
Then show the corrected code.
