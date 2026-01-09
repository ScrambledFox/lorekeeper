# LoreKeeper Phase 2: Migration & Deployment Guide

## Overview

This guide provides instructions for migrating your LoreKeeper installation from Phase 1 to Phase 2, which adds the ClaimTruth system for explicit truth value tracking.

## Prerequisites

- PostgreSQL 12+
- Alembic (already included in LoreKeeper dependencies)
- LoreKeeper application running Phase 1

## Migration Steps

### Step 1: Backup Your Database

Before running any migrations, create a backup:

```bash
# PostgreSQL backup
pg_dump -U postgres -d lorekeeper -f lorekeeper_backup_$(date +%Y%m%d_%H%M%S).sql

# Or using Docker
docker-compose exec postgres pg_dump -U postgres lorekeeper > backup.sql
```

### Step 2: Update LoreKeeper Code

Pull the latest code that includes Phase 2 implementation:

```bash
git pull origin main
```

Verify the migration file exists:
```bash
ls lorekeeper/db/migrations/versions/003_add_claim_truth.py
```

### Step 3: Apply the Migration

Run the Alembic migration:

```bash
# Apply the migration
alembic upgrade 003

# Verify the migration
alembic current
# Should output: 003_add_claim_truth (head)
```

**What happens:**
- Creates `claim` table with full subject-predicate-object structure
- Creates `snippet_analysis` table for lore analysis metadata
- Adds 6 indexes for performance optimization
- All changes are non-destructive (existing Phase 1 data is preserved)

### Step 4: Verify Migration

Check that tables were created:

```bash
# Connect to PostgreSQL
psql -U postgres -d lorekeeper

# List tables
\dt

# Check claim table structure
\d claim

# Check snippet_analysis table structure
\d snippet_analysis

# Check indexes
\di
```

Expected tables:
- `claim` - New table for truth value tracking
- `snippet_analysis` - New table for analysis metadata

### Step 5: Update Application Code

Ensure all Phase 2 dependencies are installed:

```bash
pip install -r requirements.txt

# Or if using a specific requirements file
pip install -r requirements-phase2.txt
```

### Step 6: Restart Application

```bash
# If using standalone app
python -m lorekeeper.api.main

# If using Docker
docker-compose restart api

# If using uvicorn directly
uvicorn lorekeeper.api.main:app --reload
```

### Step 7: Run Tests

Verify everything works:

```bash
# Run all tests
pytest lorekeeper/tests/ -v

# Run claim-specific tests
pytest lorekeeper/tests/test_claims.py -v
pytest lorekeeper/tests/test_claim_endpoints.py -v
pytest lorekeeper/tests/test_retrieval_truth_filtering.py -v
```

## Rollback Procedure

If you need to rollback to Phase 1:

### Step 1: Downgrade Database

```bash
# Downgrade migration
alembic downgrade 002

# Verify
alembic current
# Should output: 002_add_is_fiction_to_entity (head)
```

### Step 2: Restart Application

```bash
# Restart with Phase 1 code
docker-compose restart api
# Or restart your application normally
```

## Migration Verification Checklist

- [ ] Database backed up
- [ ] Migration file exists (`003_add_claim_truth.py`)
- [ ] Alembic upgrade completed successfully
- [ ] New tables exist (`claim`, `snippet_analysis`)
- [ ] Indexes created
- [ ] Application restarted
- [ ] Tests pass
- [ ] API endpoints accessible at `/worlds/{world_id}/claims`
- [ ] No Phase 1 data was lost or corrupted

## Common Issues & Solutions

### Issue: Migration Already Applied

**Error:** `AlembicError: Can't resolve symbol 'None' in the scope of <Enum object>`

**Solution:** Check the current migration:
```bash
alembic current
```

If already on 003, you can safely proceed.

### Issue: Migration Fails with Foreign Key Error

**Error:** `IntegrityError: ... foreign key constraint`

**Solution:**
1. Verify all referenced tables exist
2. Check that `world` table exists from Phase 1
3. Run migration in transaction:
```bash
alembic upgrade 003
```

If still failing, restore from backup and report the issue.

### Issue: New Tables Don't Appear

**Error:** `ProgrammingError: relation "claim" does not exist`

**Solution:**
1. Verify migration ran: `alembic current`
2. Check PostgreSQL logs
3. Manually verify table existence:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema='public' AND table_name='claim';
```

### Issue: Port Already in Use

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn lorekeeper.api.main:app --port 8001
```

## Performance Optimization

### Verify Indexes

After migration, verify indexes are created:

```sql
SELECT indexname, tablename FROM pg_indexes
WHERE tablename IN ('claim', 'snippet_analysis')
ORDER BY tablename, indexname;
```

Expected indexes:
- `idx_claim_world_id`
- `idx_claim_subject_entity_id`
- `idx_claim_object_entity_id`
- `idx_claim_truth_status`
- `idx_claim_snippet_id`
- `idx_claim_predicate`
- `idx_snippet_analysis_snippet_id`
- `idx_snippet_analysis_world_id`

### Vacuum and Analyze (Optional)

After migration, optimize the database:

```bash
# Connect to PostgreSQL
psql -U postgres -d lorekeeper

# Vacuum and analyze
VACUUM ANALYZE;

# Exit
\q
```

## Production Deployment Checklist

- [ ] Code reviewed and tested locally
- [ ] Database backup completed
- [ ] Staging environment upgraded first
- [ ] Tests pass in staging
- [ ] Performance benchmarks acceptable
- [ ] Rollback procedure documented and tested
- [ ] Stakeholders notified of downtime (if any)
- [ ] Application monitoring configured
- [ ] Logs monitored during deployment
- [ ] Users notified after successful upgrade

## Post-Migration Steps

### 1. Verify API Endpoints

```bash
# Create a test world and entity first, then:

# Create a claim
curl -X POST http://localhost:8000/worlds/{world_id}/claims \
  -H "Content-Type: application/json" \
  -d '{
    "subject_entity_id": "{entity_id}",
    "predicate": "test_claim",
    "truth_status": "CANON_TRUE"
  }'

# List claims
curl http://localhost:8000/worlds/{world_id}/claims

# Should return 201 Created and the new claim
```

### 2. Monitor Application Logs

Watch for any errors in the application logs:

```bash
# Docker logs
docker-compose logs -f api

# Or direct logs
tail -f application.log
```

### 3. Run Comprehensive Tests

```bash
# Full test suite
pytest lorekeeper/tests/ -v --tb=short

# With coverage report (if installed)
pytest lorekeeper/tests/ --cov=lorekeeper --cov-report=html
```

### 4. Update Documentation

- [ ] Update API documentation
- [ ] Update user guides
- [ ] Document new features for team
- [ ] Create tutorial for claims system

## Data Migration (Optional)

If you want to extract claims from existing snippets:

```python
# In a Python script or Jupyter notebook
from lorekeeper.api.services.claim_extractor import extract_claims_from_snippet
from lorekeeper.db.database import SessionLocal
from lorekeeper.db.models import DocumentSnippet

db = SessionLocal()

# Get all snippets
snippets = db.query(DocumentSnippet).all()

# Extract claims for each snippet
for snippet in snippets:
    claims = extract_claims_from_snippet(
        snippet_id=snippet.id,
        world_id=snippet.world_id,
        db=db,
        strategy="mention_based"
    )
    print(f"Extracted {len(claims)} claims from snippet {snippet.id}")

db.close()
print("Extraction complete!")
```

## Support

If you encounter issues during migration:

1. Check the troubleshooting section above
2. Review application logs for specific errors
3. Run test suite to identify failing components
4. Consult Phase 2 implementation documentation
5. Report issues with:
   - Error messages
   - Database logs
   - Application logs
   - Steps to reproduce

## Timeline

**Phase 1 → Phase 2 Migration:**
- Database migration: ~1-5 minutes
- Application restart: ~10-30 seconds
- Tests: ~1-2 minutes
- **Total estimated time: 5-10 minutes**

**Zero downtime deployments:**
- Deploy new code (Phase 1 still running)
- Run migration
- Restart application
- Verify endpoints
- Rollback available if needed

---

For questions or issues, refer to the Phase 2 documentation or implementation guide.
