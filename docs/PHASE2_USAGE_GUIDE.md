# LoreKeeper Phase 2: ClaimTruth System - Usage Guide

## Overview

The ClaimTruth system provides explicit truth value tracking for lore in LoreKeeper. This enables differentiation between canonical facts, false rumors, in-world beliefs, and unknown claims.

## Core Concepts

### Truth Values

- **CANON_TRUE**: Verified canonical facts (e.g., "King Aldren died in Year 1032")
- **CANON_FALSE**: Known false rumors or debunked myths (e.g., "He rules from beneath the lake")
- **UNKNOWN**: Unverified claims that may be true or false (e.g., "His treasure is hidden")
- **IN_WORLD_TRUE**: Widely believed but status unknown (e.g., "Aldren is magical")

### Contradiction Detection

Contradictions are assessed when claims are created:

1. **CANON_TRUE claims**: Rejected if they contradict existing CANON_FALSE claims with the same subject and predicate
2. **CANON_FALSE claims**: Rejected if a CANON_TRUE version already exists with the same subject and predicate
3. **UNKNOWN & IN_WORLD_TRUE**: Bypass contradiction checks

## API Endpoints

### Create a Claim

```bash
POST /worlds/{world_id}/claims
Content-Type: application/json

{
  "subject_entity_id": "uuid",
  "predicate": "died_in",
  "object_text": "Year 1032",
  "truth_status": "CANON_TRUE",
  "snippet_id": "uuid (optional)",
  "notes": "Verified from the Chronicle of Kings"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "world_id": "uuid",
  "subject_entity_id": "uuid",
  "predicate": "died_in",
  "object_text": "Year 1032",
  "object_entity_id": null,
  "truth_status": "CANON_TRUE",
  "snippet_id": null,
  "notes": "Verified from the Chronicle of Kings",
  "created_at": "2025-01-09T10:30:00Z",
  "updated_at": "2025-01-09T10:30:00Z"
}
```

**Error Response (409 Conflict - Contradiction Detected):**
```json
{
  "detail": "Lore inconsistency: New CANON_TRUE claim contradicts existing CANON_FALSE claim (id: {existing_claim_id}). He's actually dead"
}
```

### Retrieve a Claim

```bash
GET /worlds/{world_id}/claims/{claim_id}
```

**Response:**
```json
{
  "id": "uuid",
  "world_id": "uuid",
  "subject_entity_id": "uuid",
  "predicate": "died_in",
  "object_text": "Year 1032",
  "object_entity_id": null,
  "truth_status": "CANON_TRUE",
  "snippet_id": null,
  "notes": "Verified from the Chronicle of Kings",
  "created_at": "2025-01-09T10:30:00Z",
  "updated_at": "2025-01-09T10:30:00Z"
}
```

### List Claims

```bash
GET /worlds/{world_id}/claims
```

**Query Parameters:**
- `entity_id`: Filter by subject entity UUID
- `truth_status`: Filter by truth value (CANON_TRUE, CANON_FALSE, UNKNOWN, IN_WORLD_TRUE)
- `predicate`: Filter by predicate string
- `skip`: Number of results to skip (default: 0)
- `limit`: Maximum results to return (default: 100)

**Example:**
```bash
GET /worlds/{world_id}/claims?truth_status=CANON_TRUE&entity_id={uuid}&limit=10
```

**Response:**
```json
[
  {
    "id": "uuid",
    "world_id": "uuid",
    "subject_entity_id": "uuid",
    "predicate": "died_in",
    "object_text": "Year 1032",
    "object_entity_id": null,
    "truth_status": "CANON_TRUE",
    "snippet_id": null,
    "notes": "Verified from the Chronicle of Kings",
    "created_at": "2025-01-09T10:30:00Z",
    "updated_at": "2025-01-09T10:30:00Z"
  }
]
```

### Update a Claim

```bash
PATCH /worlds/{world_id}/claims/{claim_id}
Content-Type: application/json

{
  "truth_status": "CANON_FALSE",
  "notes": "Updated note"
}
```

**Response:**
```json
{
  "id": "uuid",
  "world_id": "uuid",
  "subject_entity_id": "uuid",
  "predicate": "died_in",
  "object_text": "Year 1032",
  "object_entity_id": null,
  "truth_status": "CANON_FALSE",
  "snippet_id": null,
  "notes": "Updated note",
  "created_at": "2025-01-09T10:30:00Z",
  "updated_at": "2025-01-09T11:00:00Z"
}
```

### Delete a Claim

```bash
DELETE /worlds/{world_id}/claims/{claim_id}
```

**Response:**
```json
{
  "message": "Claim deleted"
}
```

## Common Workflows

### Scenario 1: Recording a Historical Fact

```bash
# Create a canonical fact about a character
POST /worlds/{world_id}/claims
{
  "subject_entity_id": "king_aldren_id",
  "predicate": "died_in",
  "object_text": "Year 1032",
  "truth_status": "CANON_TRUE",
  "notes": "Documented in royal records"
}
```

### Scenario 2: Recording a False Rumor

```bash
# Record a rumor that the community knows is false
POST /worlds/{world_id}/claims
{
  "subject_entity_id": "king_aldren_id",
  "predicate": "is_alive",
  "truth_status": "CANON_FALSE",
  "notes": "False rumor spread after his death"
}
```

### Scenario 3: Recording an Unknown/Unverified Fact

```bash
# Record something that might be true but is unverified
POST /worlds/{world_id}/claims
{
  "subject_entity_id": "king_aldren_id",
  "predicate": "has_hidden_treasure",
  "truth_status": "UNKNOWN",
  "notes": "Mentioned in some folklore, unverified"
}
```

### Scenario 4: Retrieving Canon Facts Only

```bash
# Get all verified facts about an entity
GET /worlds/{world_id}/claims?entity_id={king_aldren_id}&truth_status=CANON_TRUE
```

### Scenario 5: Handling Contradiction Error

When creating a claim that contradicts existing data:

```bash
# First: Create a canonical fact
POST /worlds/{world_id}/claims
{
  "subject_entity_id": "king_aldren_id",
  "predicate": "died_in",
  "object_text": "Year 1032",
  "truth_status": "CANON_TRUE"
}
# Response: 201 Created

# Later: Try to create contradictory fact
POST /worlds/{world_id}/claims
{
  "subject_entity_id": "king_aldren_id",
  "predicate": "died_in",
  "object_text": "Year 1050",
  "truth_status": "CANON_TRUE"
}
# Response: 409 Conflict
# Detail: "Lore inconsistency: New CANON_TRUE claim contradicts existing CANON_FALSE claim..."
```

## Retrieval Integration

### Retrieving Snippets by Truth Status

The retrieval service now supports truth-status filtering:

```python
# Import the retrieval service
from lorekeeper.api.services.retrieval import RetrievalPolicy, RetrievalService

# Available truth-status policies:
# - RetrievalPolicy.HYBRID (default, no filtering)
# - RetrievalPolicy.CANON_TRUE_ONLY (only canonically verified)
# - RetrievalPolicy.NO_CANON_FALSE (exclude false claims)
# - RetrievalPolicy.IN_WORLD_BELIEFS (canon + widely believed)

# Example: Get only verified facts
snippets = await RetrievalService.retrieve_snippets_by_truth_status(
    session=db_session,
    world_id=world_id,
    query_embedding=embedding_vector,
    policy="STRICT_ONLY",  # Document policy (STRICT/MYTHIC)
    truth_policy="CANON_TRUE_ONLY",  # Truth status policy
    limit=10
)
```

## Extraction Service

### Extracting Claims from Snippets

```python
from lorekeeper.api.services.claim_extractor import extract_claims_from_snippet

# Extract claims from a snippet (MVP: mention-based)
claims = extract_claims_from_snippet(
    snippet_id=snippet_id,
    world_id=world_id,
    db=db_session,
    strategy="mention_based"  # Currently only strategy available
)
```

This creates UNKNOWN claims for each entity mentioned in the snippet.

## Error Handling

### Contradiction Errors (409 Conflict)

```json
{
  "detail": "Lore inconsistency: New CANON_TRUE claim contradicts existing CANON_FALSE claim (id: uuid). Previous notes: ..."
}
```

**Resolution:**
1. Review the conflicting claim (check the UUID in the error)
2. Decide if the new claim should override the old one
3. Delete the old claim and create the new one, OR
4. Modify the new claim to a different truth status (e.g., UNKNOWN instead of CANON_TRUE)

### Not Found Errors (404)

```json
{
  "detail": "Claim not found"
}
```

Occurs when trying to retrieve/update/delete a non-existent claim.

### Invalid World (404)

```json
{
  "detail": "World not found"
}
```

Occurs when the world_id doesn't exist.

## Best Practices

### 1. Use Clear Predicates

Choose predicates that clearly describe relationships:
- `died_in` instead of `death_time`
- `rules_from` instead of `location`
- `has_age` instead of `age_value`

### 2. Set Appropriate Truth Values

- Use **CANON_TRUE** for verified, documented facts
- Use **CANON_FALSE** for known false rumors or debunked myths
- Use **UNKNOWN** for unverified claims from documents
- Use **IN_WORLD_TRUE** for widely believed but status-uncertain claims

### 3. Add Descriptive Notes

Always include notes explaining the source or reasoning:
```json
{
  "notes": "Verified from the Royal Chronicle, Vol. 3, Page 47"
}
```

### 4. Link to Snippets

When extracting claims from documents, link them to the snippet:
```json
{
  "snippet_id": "uuid_of_source_snippet",
  "notes": "Extracted from passage at char 100-150"
}
```

### 5. Handle Contradictions Carefully

When getting a 409 error:
1. Read the conflicting claim ID
2. Fetch that claim to understand the conflict
3. Make an informed decision about resolution
4. Don't silently fail; surface the error to the user

## Database Schema Reference

### claim table

```sql
CREATE TABLE claim (
    id UUID PRIMARY KEY,
    world_id UUID NOT NULL REFERENCES world(id),
    snippet_id UUID REFERENCES document_snippet(id),
    claimed_by_entity_id UUID REFERENCES entity(id),
    subject_entity_id UUID REFERENCES entity(id),
    predicate VARCHAR(255) NOT NULL,
    object_text TEXT,
    object_entity_id UUID REFERENCES entity(id),
    truth_status VARCHAR(50) NOT NULL,  -- CANON_TRUE, CANON_FALSE, UNKNOWN, IN_WORLD_TRUE
    canon_ref_entity_version_id UUID,
    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### Indexes

- `idx_claim_world_id` - Fast lookup by world
- `idx_claim_subject_entity_id` - Fast lookup by subject
- `idx_claim_truth_status` - Fast filtering by truth value
- `idx_claim_snippet_id` - Fast lookup by source snippet
- `idx_claim_predicate` - Fast filtering by predicate

## Testing

### Run Tests

```bash
# Unit tests for models
pytest lorekeeper/tests/test_claims.py -v

# Integration tests for endpoints
pytest lorekeeper/tests/test_claim_endpoints.py -v

# Retrieval tests
pytest lorekeeper/tests/test_retrieval_truth_filtering.py -v

# All tests
pytest lorekeeper/tests/ -v -k claim
```

## Migration

The Phase 2 implementation includes a database migration:

```bash
# Apply migration
alembic upgrade 003

# Rollback migration
alembic downgrade 002
```

## Next Steps (Phase 3)

- LLM-based claim extraction with more nuanced predicates
- Semantic contradiction detection
- NPC knowledge base implementation
- Confidence scoring for contradictions
- Advanced agentic pipeline integration
