# Quickstart: Checklist Data Layer

## Implementation Steps

1. **Create Models**: Add the new model files to `backend/packages/db/db/models/`:
   - `users.py`
   - `unique_targets.py`
   - `user_scans.py`
   - `scan_results.py`
2. **Export Models**: Update `backend/packages/db/db/models/__init__.py` to export the new models.
3. **Alembic Migration**:
   ```bash
   task backend:migration -- "add checklist models"
   ```
4. **Apply Migration**:
   ```bash
   task backend:migrate
   ```

## Local Development Verification

1. **Start Services**: `task dev` (ensure PostgreSQL is running).
2. **Run Tests**:
   ```bash
   uv run pytest backend/packages/db/tests/test_models.py
   ```

## Key Code Snippets

### Unique Hashing (unique_targets.py)

```python
import hashlib

def calculate_hash(provider_id: int, campground_id: str, start_date: date, end_date: date) -> str:
    hash_input = f"{provider_id}:{campground_id}:{start_date.isoformat()}:{end_date.isoformat()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()
```
