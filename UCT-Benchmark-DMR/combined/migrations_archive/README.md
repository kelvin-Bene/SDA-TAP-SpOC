# Legacy Migrations (Archived)

These SQL migration files are from the original manual migration system
used before the project adopted Alembic for database schema management.

They are preserved here for historical reference only. **Do not run these
files directly.**

All new migrations should be created and managed through Alembic:

```bash
# Create a new migration
DATABASE_URL=postgresql://... alembic revision -m "description"

# Apply pending migrations
DATABASE_URL=postgresql://... alembic upgrade head

# Check current version
DATABASE_URL=postgresql://... alembic current
```

See `alembic/versions/` for the active migration chain.
