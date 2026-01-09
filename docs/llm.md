# LoreKeeper API Guide for Document & Lore Writing LLMs

This guide describes how to use the LoreKeeper API as an agentic LLM system for worldbuilding, lore management, and document generation.

## Overview

LoreKeeper is a knowledge management system for generated worlds that distinguishes between:
- **Canonical Lore** (STRICT mode): Established facts about the world
- **Mythic Lore** (MYTHIC mode): Stories, rumors, and beliefs

The API allows you to:
1. Create and manage worlds
2. Define canonical entities (characters, locations, factions, etc.)
3. Store documents and narrative content
4. Link entities to document snippets
5. Extract and query claims about the world
6. Retrieve relevant lore based on semantic similarity

## Authentication & Setup

All requests should be made to: `http://localhost:8000`

No authentication is required for local development.

## Core Concepts

### Worlds
A "world" is the top-level container for all lore in a campaign or setting.

```
World
├── Entities (canonical facts)
├── Documents (source texts)
└── Claims (atomic statements)
```

### Entities
Entities are canonical facts about your world. Each entity has:
- **Type**: Character, Location, Faction, Creature, Object, Event
- **Canonical Name**: The official name in your world
- **Aliases**: Alternative names (e.g., "The Great King" for "King Aldren")
- **Tags**: Categorization tags
- **is_fiction**: Boolean - true if it's a fictional entity within the world's beliefs

### Documents
Documents are source texts in your world. Each document has:
- **Mode**: STRICT (canonical facts) or MYTHIC (stories, rumors, beliefs)
- **Kind**: CHRONICLE, SCRIPTURE, BALLAD, RUMOR, TEXTBOOK, ARTIFACT, etc.
- **Author**: Who wrote/told this in-world
- **In-World Date**: When this was written/told
- **Provenance**: Metadata about the source

### Document Snippets
Documents are automatically chunked into semantic snippets for retrieval. Each snippet includes:
- Text content
- Vector embedding (for semantic search)
- Position tracking

### Entity Mentions
Links between entities and document snippets with confidence scoring.

### Claims
Atomic statements (subject-predicate-object triples) extracted from documents:
- **Subject**: An entity
- **Predicate**: A relationship or property
- **Object**: Text or another entity
- **Truth Status**: CANON_TRUE or CANON_FALSE
- **Belief Prevalence**: How widely believed (0.0 = unknown, 1.0 = universal)

## API Endpoints

### World Management

#### Create a World
```http
POST /worlds
Content-Type: application/json

{
  "name": "Aethermoor",
  "description": "A mystical realm where ancient magic flows through forgotten kingdoms."
}
```

Response:
```json
{
  "id": "uuid",
  "name": "Aethermoor",
  "description": "A mystical realm...",
  "created_at": "2025-01-09T10:00:00",
  "updated_at": "2025-01-09T10:00:00"
}
```

#### Get World by ID
```http
GET /worlds/{world_id}
```

### Entity Management

#### Create an Entity
```http
POST /worlds/{world_id}/entities
Content-Type: application/json

{
  "type": "Character",
  "canonical_name": "King Aldren",
  "aliases": ["Aldren the Wise", "The Last King"],
  "summary": "Ruler of the Northern Kingdoms",
  "description": "King Aldren ruled from 1000 to 1032, known for diplomatic prowess...",
  "tags": ["ruler", "diplomat", "ancient_lore", "deceased"],
  "is_fiction": false
}
```

#### Get Entity
```http
GET /worlds/{world_id}/entities/{entity_id}
```

#### Update Entity
```http
PATCH /worlds/{world_id}/entities/{entity_id}
Content-Type: application/json

{
  "description": "Updated description...",
  "tags": ["ruler", "diplomat", "legendary"]
}
```

#### Search Entities
```http
POST /worlds/{world_id}/entities/search
Query Parameters:
  - query: "search term" (searches canonical_name, aliases, summary, description, tags)
  - entity_type: "Character" (filter by type)
  - limit: 20 (default)
  - offset: 0 (for pagination)
```

Response:
```json
{
  "total": 42,
  "results": [
    {
      "id": "uuid",
      "world_id": "uuid",
      "type": "Character",
      "canonical_name": "King Aldren",
      "aliases": ["Aldren the Wise", "The Last King"],
      "summary": "...",
      "description": "...",
      "tags": ["ruler", "diplomat"],
      "is_fiction": false,
      "created_at": "2025-01-09T10:00:00",
      "updated_at": "2025-01-09T10:00:00"
    }
  ]
}
```

### Document Management

#### Create a Document
```http
POST /worlds/{world_id}/documents
Content-Type: application/json

{
  "mode": "STRICT",
  "kind": "CHRONICLE",
  "title": "The Annals of the Northern Kingdoms",
  "author": "Lord Archivist Matthus",
  "in_world_date": "Year 1150",
  "text": "The Northern Kingdoms were ruled by the line of Aldren...",
  "provenance": {
    "source": "historical_archive",
    "authenticity": "high",
    "verified": true
  }
}
```

Response includes:
```json
{
  "id": "uuid",
  "world_id": "uuid",
  "mode": "STRICT",
  "kind": "CHRONICLE",
  "title": "The Annals of the Northern Kingdoms",
  "author": "Lord Archivist Matthus",
  "in_world_date": "Year 1150",
  "text": "...",
  "provenance": {"source": "historical_archive", ...},
  "snippets": [
    {
      "id": "uuid",
      "snippet_index": 0,
      "start_char": 0,
      "end_char": 150,
      "snippet_text": "The Northern Kingdoms were ruled...",
      "embedding": [0.1, 0.2, ...]
    }
  ]
}
```

#### Get Document
```http
GET /worlds/{world_id}/documents/{document_id}
```

### Entity Mentions

#### Create Entity Mention
Links an entity to a document snippet with confidence.

```http
POST /worlds/{world_id}/mentions
Content-Type: application/json

{
  "snippet_id": "uuid",
  "entity_id": "uuid",
  "mention_text": "King Aldren",
  "confidence": 0.95
}
```

#### Get Mention
```http
GET /worlds/{world_id}/mentions/{mention_id}
```

### Claims

#### Create Claim
```http
POST /worlds/{world_id}/claims
Content-Type: application/json

{
  "subject_entity_id": "uuid",
  "predicate": "has_residence",
  "object_text": "Northern Kingdoms",
  "truth_status": "CANON_TRUE",
  "belief_prevalence": 0.95,
  "notes": "Documented in the Annals"
}
```

#### Get Claim
```http
GET /worlds/{world_id}/claims/{claim_id}
```

#### Query Claims by Entity
```http
GET /worlds/{world_id}/claims?subject_entity_id={entity_id}
```

### Retrieval (Semantic Search)

The retrieval endpoint uses vector embeddings and truth status to find relevant lore.

```http
POST /worlds/{world_id}/retrieve
Content-Type: application/json

{
  "query": "What happened to King Aldren?",
  "policy": "HYBRID",
  "limit": 10,
  "truth_filter": "NO_CANON_FALSE"
}
```

**Policy Options:**
- `STRICT_ONLY`: Only canonical documents
- `MYTHIC_ONLY`: Only mythic/belief documents
- `HYBRID`: Both, ranked by type
- `IN_WORLD_BELIEFS`: All documents from the world's perspective

**Truth Filter Options:**
- `CANON_TRUE_ONLY`: Only canonically true claims
- `NO_CANON_FALSE`: Exclude canonically false claims
- `IN_WORLD_BELIEFS`: Include all as potential beliefs

Response:
```json
{
  "query": "What happened to King Aldren?",
  "policy": "HYBRID",
  "results": [
    {
      "snippet": {
        "id": "uuid",
        "document_id": "uuid",
        "snippet_text": "King Aldren died in the year 1032...",
        "embedding": [...]
      },
      "document": {
        "id": "uuid",
        "mode": "STRICT",
        "kind": "CHRONICLE",
        "title": "The Annals of the Northern Kingdoms",
        "author": "Lord Archivist Matthus"
      },
      "similarity_score": 0.87,
      "mentions": [
        {
          "entity_id": "uuid",
          "canonical_name": "King Aldren",
          "confidence": 0.95
        }
      ],
      "claims": [
        {
          "id": "uuid",
          "predicate": "died_in_year",
          "object_text": "1032",
          "truth_status": "CANON_TRUE",
          "belief_prevalence": 0.95
        }
      ]
    }
  ]
}
```

## Workflows for LLM Agents

### Workflow 1: Creating a New World with Entities

1. **Create the world**
   ```
   POST /worlds
   ```

2. **Define key entities** (characters, locations, factions)
   ```
   POST /worlds/{world_id}/entities
   ```

3. **Document canonical facts**
   ```
   POST /worlds/{world_id}/documents (mode=STRICT)
   ```

4. **Link entities to documents**
   ```
   POST /worlds/{world_id}/mentions
   ```

### Workflow 2: Adding Rumors and Beliefs

1. **Create a mythic document**
   ```
   POST /worlds/{world_id}/documents (mode=MYTHIC)
   ```

2. **Link entities mentioned in the story**
   ```
   POST /worlds/{world_id}/mentions
   ```

3. **Extract and record claims**
   ```
   POST /worlds/{world_id}/claims (truth_status=CANON_FALSE or unknown)
   ```

### Workflow 3: Querying Existing Lore

1. **Search for relevant snippets**
   ```
   POST /worlds/{world_id}/retrieve
   ```

2. **Analyze results** to understand:
   - What is canonically established
   - What are common beliefs
   - What contradictions exist
   - What gaps exist in the lore

3. **Generate new content** based on gaps or to resolve contradictions

### Workflow 4: Contradiction Detection

1. **Create conflicting claims**
   ```
   POST /worlds/{world_id}/claims (truth_status=CANON_TRUE)
   POST /worlds/{world_id}/claims (truth_status=CANON_FALSE)
   ```

2. **Query for contradictions**
   ```
   POST /worlds/{world_id}/retrieve
   ```

3. **Use contradiction information** to generate reconciling narratives or clarifications

## Best Practices for LLM Agents

### Entity Management
- Use `is_fiction: false` for entities that are "real" in the world
- Use `is_fiction: true` for entities that are believed to be legendary or mythical
- Use descriptive aliases to capture how entities are referenced in different documents
- Tag entities for easy categorization (e.g., "royalty", "deceased", "legendary")

### Document Organization
- Use `STRICT` mode for:
  - Historical records
  - Official chronicles
  - Established canon
  - Documented facts

- Use `MYTHIC` mode for:
  - Legends and folklore
  - Rumors and gossip
  - Religious texts and prophecies
  - Bard's tales and stories

### Claim Extraction
- Extract specific, atomic claims (subject-predicate-object)
- Use `belief_prevalence` to indicate how widely known a claim is
  - 0.0-0.3: Obscure or forgotten
  - 0.3-0.7: Semi-known, debated
  - 0.7-1.0: Widely accepted

### Semantic Search
- Use specific, natural language queries
- Use `HYBRID` policy for comprehensive search
- Use `IN_WORLD_BELIEFS` to see the world from the inhabitants' perspective
- Use `NO_CANON_FALSE` to avoid contradictions in search results

### Content Generation
1. **Retrieve context** with specific queries
2. **Check for contradictions** in results
3. **Identify gaps** in the lore
4. **Generate coherent content** that fills gaps or develops existing themes
5. **Store results** via document and entity endpoints

## Error Handling

### Common Status Codes

- `200 OK`: Successful retrieval
- `201 Created`: Successfully created resource
- `400 Bad Request`: Invalid request format or data
- `404 Not Found`: Entity or document doesn't exist
- `409 Conflict`: Constraint violation (e.g., duplicate entity name)
- `422 Unprocessable Entity`: Validation error in request body

### Error Response Format

```json
{
  "detail": "Entity not found"
}
```

## Rate Limiting & Performance

- Batch operations when possible (create multiple entities/documents together)
- Use pagination for large result sets (limit, offset)
- Semantic search can be resource-intensive; consider caching results
- Document uploads are chunked automatically; no file size limit for typical use

## Example: Creating a Coherent Lore Database

```python
# Pseudocode for an LLM agent

# 1. Create the world
world = create_world("Aethermoor", "A realm of ancient magic...")

# 2. Define canonical entities
king = create_entity(world,
  type="Character",
  name="King Aldren",
  description="Ruler of the Northern Kingdoms",
  is_fiction=False
)

lake = create_entity(world,
  type="Location",
  name="Lake Silvermere",
  description="An ancient magical lake",
  is_fiction=False
)

# 3. Document canon
canon_doc = create_document(world,
  mode="STRICT",
  title="The Annals",
  text="King Aldren ruled from 1000 to 1032..."
)

# 4. Link entities
create_mention(world, canon_doc.snippet[0], king)
create_mention(world, canon_doc.snippet[1], lake)

# 5. Extract claims
create_claim(world,
  subject=king,
  predicate="ruled_from",
  object="1000 to 1032",
  truth_status="CANON_TRUE"
)

# 6. Add mythic version
myth_doc = create_document(world,
  mode="MYTHIC",
  title="The Tale of Aldren the Immortal",
  text="Some say Aldren sought refuge beneath Lake Silvermere..."
)

create_claim(world,
  subject=king,
  predicate="sought_immortality",
  object="Lake Silvermere",
  truth_status="CANON_FALSE",  # It's a myth
  belief_prevalence=0.2
)

# 7. Query the lore
results = retrieve(world,
  query="What happened to King Aldren?",
  policy="HYBRID"
)

# Results include both the factual account and the mythic version
# The LLM can now generate coherent narratives that respect both
```

## Advanced Features

### Belief Prevalence Tracking
Use belief prevalence to model how knowledge spreads:
- A rumor starts with low prevalence (0.1)
- As more people believe it, increase prevalence
- Ancient myths might have moderate prevalence (0.3-0.5)
- Well-established facts have high prevalence (0.9+)

### Truth Status Paradoxes
A single entity can have multiple contradictory claims:
- Canon says "Aldren died"
- Myth says "Aldren is immortal"

Use different documents and truth statuses to represent both perspectives.

### Provenance Tracking
Use the `provenance` field to track sources:
```json
{
  "source": "royal_archive",
  "discovered_by": "Scholar Matthus",
  "authenticity": "verified",
  "confidence": 0.95
}
```

## Testing Your Integration

To verify your LLM agent's integration:

1. Create a test world
2. Create 3-5 entities
3. Add documents linking entities
4. Query for entities and documents
5. Perform semantic search with various policies
6. Verify contradiction handling

All operations should complete within seconds.

## Support & Debugging

### Enable Debug Logging
The API includes detailed logging for development:
- Enable in docker-compose.yml with `DB_ECHO=true`
- Check logs: `docker-compose logs api`

### Verify Database State
Use the `/worlds/{world_id}/entities` search endpoint to verify what's stored.

### Common Issues

**Issue**: Entity not found after creation
- Solution: Verify the `world_id` matches

**Issue**: Semantic search returns no results
- Solution: Ensure document snippets exist and embeddings were generated

**Issue**: Claims not appearing in retrieval results
- Solution: Verify claims are linked to snippets via mentions

## Next Steps

1. Implement entity creation and management
2. Add document ingestion and chunking
3. Implement semantic retrieval
4. Build claim extraction logic
5. Develop narrative generation on top of the API

This API provides the foundation for coherent, scalable worldbuilding with LLM agents.
