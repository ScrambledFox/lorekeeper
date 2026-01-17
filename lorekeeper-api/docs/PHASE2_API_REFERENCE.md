# LoreKeeper Phase 2: ClaimTruth API Reference

## Base URL

All endpoints are prefixed with: `/worlds/{world_id}`

## Claims Endpoints

### Create Claim

**Endpoint:** `POST /worlds/{world_id}/claims`

**Description:** Create a new claim with automatic contradiction detection.

**Request Body:**
```json
{
  "subject_entity_id": "uuid | null",
  "predicate": "string (required, 1-255 chars)",
  "object_text": "string | null",
  "object_entity_id": "uuid | null",
  "truth_status": "CANON_TRUE | CANON_FALSE | UNKNOWN | IN_WORLD_TRUE (default: UNKNOWN)",
  "snippet_id": "uuid | null",
  "notes": "string | null"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "world_id": "uuid",
  "subject_entity_id": "uuid | null",
  "predicate": "string",
  "object_text": "string | null",
  "object_entity_id": "uuid | null",
  "truth_status": "CANON_TRUE | CANON_FALSE | UNKNOWN | IN_WORLD_TRUE",
  "snippet_id": "uuid | null",
  "notes": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Possible Errors:**
- `404 Not Found` - World doesn't exist
- `409 Conflict` - Claim contradicts existing claims
  - CANON_TRUE contradicts CANON_FALSE with same subject+predicate
  - CANON_FALSE contradicts existing CANON_TRUE

**Example:**
```bash
curl -X POST http://localhost:8000/worlds/{world_id}/claims \
  -H "Content-Type: application/json" \
  -d '{
    "subject_entity_id": "abc123",
    "predicate": "died_in",
    "object_text": "Year 1032",
    "truth_status": "CANON_TRUE",
    "notes": "From royal records"
  }'
```

---

### Get Claim

**Endpoint:** `GET /worlds/{world_id}/claims/{claim_id}`

**Description:** Retrieve a specific claim by ID.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "world_id": "uuid",
  "subject_entity_id": "uuid | null",
  "predicate": "string",
  "object_text": "string | null",
  "object_entity_id": "uuid | null",
  "truth_status": "CANON_TRUE | CANON_FALSE | UNKNOWN | IN_WORLD_TRUE",
  "snippet_id": "uuid | null",
  "notes": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Possible Errors:**
- `404 Not Found` - Claim doesn't exist

**Example:**
```bash
curl http://localhost:8000/worlds/{world_id}/claims/{claim_id}
```

---

### List Claims

**Endpoint:** `GET /worlds/{world_id}/claims`

**Description:** List all claims with optional filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | uuid | Filter by subject entity UUID |
| `truth_status` | string | Filter by truth value (CANON_TRUE, CANON_FALSE, UNKNOWN, IN_WORLD_TRUE) |
| `predicate` | string | Filter by predicate string |
| `skip` | integer | Number of results to skip (default: 0) |
| `limit` | integer | Max results (default: 100, max: 100) |

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "world_id": "uuid",
    "subject_entity_id": "uuid | null",
    "predicate": "string",
    "object_text": "string | null",
    "object_entity_id": "uuid | null",
    "truth_status": "CANON_TRUE | CANON_FALSE | UNKNOWN | IN_WORLD_TRUE",
    "snippet_id": "uuid | null",
    "notes": "string | null",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

**Examples:**
```bash
# List all claims in a world
curl "http://localhost:8000/worlds/{world_id}/claims"

# Filter by entity
curl "http://localhost:8000/worlds/{world_id}/claims?entity_id={entity_id}"

# Filter by truth status
curl "http://localhost:8000/worlds/{world_id}/claims?truth_status=CANON_TRUE"

# Combined filters with pagination
curl "http://localhost:8000/worlds/{world_id}/claims?entity_id={entity_id}&truth_status=CANON_TRUE&skip=0&limit=10"
```

---

### Update Claim

**Endpoint:** `PATCH /worlds/{world_id}/claims/{claim_id}`

**Description:** Update a claim's truth status or notes.

**Request Body:**
```json
{
  "truth_status": "CANON_TRUE | CANON_FALSE | UNKNOWN | IN_WORLD_TRUE | null (optional)",
  "notes": "string | null (optional)"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "world_id": "uuid",
  "subject_entity_id": "uuid | null",
  "predicate": "string",
  "object_text": "string | null",
  "object_entity_id": "uuid | null",
  "truth_status": "CANON_TRUE | CANON_FALSE | UNKNOWN | IN_WORLD_TRUE",
  "snippet_id": "uuid | null",
  "notes": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Possible Errors:**
- `404 Not Found` - Claim doesn't exist

**Example:**
```bash
curl -X PATCH http://localhost:8000/worlds/{world_id}/claims/{claim_id} \
  -H "Content-Type: application/json" \
  -d '{
    "truth_status": "CANON_FALSE",
    "notes": "Updated evidence"
  }'
```

---

### Delete Claim

**Endpoint:** `DELETE /worlds/{world_id}/claims/{claim_id}`

**Description:** Delete a claim permanently.

**Response (200 OK):**
```json
{
  "message": "Claim deleted"
}
```

**Possible Errors:**
- `404 Not Found` - Claim doesn't exist

**Example:**
```bash
curl -X DELETE http://localhost:8000/worlds/{world_id}/claims/{claim_id}
```

---

## Data Types

### Truth Status (Enum)

Values: `CANON_TRUE`, `CANON_FALSE`, `UNKNOWN`, `IN_WORLD_TRUE`

- **CANON_TRUE**: Verified canonical facts
- **CANON_FALSE**: Known false rumors or debunked myths
- **UNKNOWN**: Unverified claims
- **IN_WORLD_TRUE**: Widely believed but status uncertain

### Claim Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary identifier |
| `world_id` | UUID | World this claim belongs to |
| `subject_entity_id` | UUID \| null | Entity the claim is about |
| `predicate` | String | Relationship/property being claimed |
| `object_text` | String \| null | Object value as text |
| `object_entity_id` | UUID \| null | Object value as entity reference |
| `truth_status` | Enum | Truth value (CANON_TRUE, CANON_FALSE, UNKNOWN, IN_WORLD_TRUE) |
| `snippet_id` | UUID \| null | Source document snippet |
| `notes` | String \| null | Additional context |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

### Validation Rules

| Field | Rules |
|-------|-------|
| `predicate` | Required, 1-255 characters |
| `truth_status` | Must be valid enum value |
| `subject_entity_id` | Optional, must reference existing entity |
| `object_entity_id` | Optional, must reference existing entity |
| `snippet_id` | Optional, must reference existing snippet |

## Error Responses

### 404 Not Found
```json
{
  "detail": "Claim not found"
}
```

### 409 Conflict (Contradiction Detected)
```json
{
  "detail": "Lore inconsistency: New CANON_TRUE claim contradicts existing CANON_FALSE claim (id: {claim_id}). {notes_from_existing_claim}"
}
```

When this occurs:
1. Fetch the conflicting claim using the ID in the error message
2. Review both claims to understand the conflict
3. Delete the conflicting claim or modify your new claim to a different truth status
4. Retry the creation

## Rate Limiting

No rate limits are currently enforced. This may change in future versions.

## Pagination

The list endpoint supports pagination:
- `skip`: Number of items to skip (default: 0)
- `limit`: Maximum items to return (default: 100)

Example: Get items 20-30
```bash
curl "http://localhost:8000/worlds/{world_id}/claims?skip=20&limit=10"
```

## Filtering Combinations

Multiple filters are combined with AND logic:

```bash
# Get CANON_TRUE claims about a specific entity
curl "http://localhost:8000/worlds/{world_id}/claims?entity_id={id}&truth_status=CANON_TRUE"

# Get claims with a specific predicate
curl "http://localhost:8000/worlds/{world_id}/claims?predicate=died_in"

# Get unknown claims about an entity
curl "http://localhost:8000/worlds/{world_id}/claims?entity_id={id}&truth_status=UNKNOWN"
```

## Examples

### Create a Historical Fact
```bash
curl -X POST http://localhost:8000/worlds/{world_id}/claims \
  -H "Content-Type: application/json" \
  -d '{
    "subject_entity_id": "king-aldren",
    "predicate": "died_in",
    "object_text": "Year 1032",
    "truth_status": "CANON_TRUE",
    "notes": "Verified from the Royal Chronicle"
  }'
```

### Record a False Rumor
```bash
curl -X POST http://localhost:8000/worlds/{world_id}/claims \
  -H "Content-Type: application/json" \
  -d '{
    "subject_entity_id": "king-aldren",
    "predicate": "rules_from_beneath_lake",
    "truth_status": "CANON_FALSE",
    "notes": "Common myth among peasants"
  }'
```

### Get All Verified Facts About an Entity
```bash
curl "http://localhost:8000/worlds/{world_id}/claims?entity_id=king-aldren&truth_status=CANON_TRUE&limit=50"
```

### Update a Claim
```bash
curl -X PATCH http://localhost:8000/worlds/{world_id}/claims/{claim_id} \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Updated with new sources found in archive"
  }'
```

### Delete a Claim
```bash
curl -X DELETE http://localhost:8000/worlds/{world_id}/claims/{claim_id}
```

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success (GET, PATCH, DELETE) |
| 201 | Created (POST) |
| 404 | Not Found |
| 409 | Conflict (Contradiction Detected) |
| 422 | Unprocessable Entity (Validation Error) |

## Headers

### Request Headers
- `Content-Type: application/json` - Required for POST/PATCH

### Response Headers
- `Content-Type: application/json` - Always present

## Timestamps

All timestamps are in UTC format (ISO 8601):
```
2025-01-09T10:30:00Z
```
