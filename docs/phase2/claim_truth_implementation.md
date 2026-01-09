# Phase 2: ClaimTruth System Implementation Plan

## Overview

This document provides a detailed implementation plan for adding explicit truth value tracking to LoreKeeper via a `Claim` table and `ClaimTruth` enum. This enables fine-grained differentiation between canonical facts, contradictions, disputes, and in-world beliefs.

**Status**: Phase 2 (deferred from Phase 1)
**Priority**: Medium (enables NPC knowledge bases, unreliable narrator patterns, and advanced retrieval policies)
**Estimated Effort**: 3-4 weeks (assuming experienced PostgreSQL/Python/FastAPI team)

---

## 1. Goals

### 1.1 Primary Goals

1. **Explicit truth tracking**: Move from implicit truth (via document mode) to explicit truth values on individual claims.
2. **Support false information**: Cleanly represent claims known to be false, disputed, or in-world-true (widely believed but canonically false).
3. **Enable advanced retrieval**: Filter and rank results by truth status (e.g., "show only CANON_TRUE facts" or "what does the world believe?").
4. **Support NPC knowledge bases**: Different NPCs can have different beliefs; some know secrets, others believe myths.
5. **Contradiction tracking**: Detect and store relationships between contradictory claims.

### 1.2 Non-Goals

- Automated truth determination (that's a Phase 3+ AI feature)
- Graph-based reasoning about claims (Phase 3+)
- Version control for claims (Phase 3+)
- Integration with agentic pipeline (Phase 3+)

---

## 2. Core Concepts

### 2.1 Claim Definition

A **claim** is an atomic statement about the world:

```
Subject: "King Aldren"
Predicate: "died_on"
Object: "Year 1032"
Truth Status: CANON_TRUE
```

Or:

```
Subject: "King Aldren"
Predicate: "is_alive"
Object: null (boolean predicate)
Truth Status: CANON_FALSE (contradicts above)
```

Or:

```
Subject: "King Aldren"
Predicate: "rules_from_the_lake"
Object: null
Truth Status: UNKNOWN (mentioned in mythic documents, unverified)
```

### 2.2 ClaimTruth Enum

Five exhaustive truth values:

| Value | Meaning | Use Case |
|-------|---------|----------|
| `CANON_TRUE` | Verified against canonical entities/facts | Player knowledge, factual statements |
| `CANON_FALSE` | Contradicts canonical facts | Known false rumors, debunked myths |
| `UNKNOWN` | Unverified; appears in documents but not evaluated | New claims from documents |
| `DISPUTED` | Multiple sources contradict each other | "Some say X, others say Y" |
| `IN_WORLD_TRUE` | Widely believed in-world despite being canonically false | Urban legends, propaganda that "works" |

### 2.3 Claim Sources

A claim can originate from:

1. **Extracted from a document snippet** (via EntityMention + NER, or manual extraction)
2. **Canonical entity facts** (automatically generated from entity descriptions)
3. **Manual assertion** (GM or system adds a claim directly)

---

## 3. Data Model

### 3.1 New Tables

#### `claim`

```sql
CREATE TABLE claim (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    world_id UUID NOT NULL REFERENCES world(id) ON DELETE CASCADE,
    snippet_id UUID REFERENCES document_snippet(id) ON DELETE SET NULL,

    -- Triple (subject-predicate-object)
    subject_entity_id UUID REFERENCES entity(id) ON DELETE CASCADE,
    predicate TEXT NOT NULL,
    object_text TEXT,
    object_entity_id UUID REFERENCES entity(id) ON DELETE SET NULL,

    -- Truth value
    truth_status VARCHAR(50) NOT NULL,  -- CANON_TRUE, CANON_FALSE, UNKNOWN, DISPUTED, IN_WORLD_TRUE

    -- Audit trail
    canon_ref_entity_version_id UUID REFERENCES entity_version(id) ON DELETE SET NULL,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast retrieval
CREATE INDEX idx_claim_world_id ON claim(world_id);
CREATE INDEX idx_claim_subject_entity_id ON claim(subject_entity_id);
CREATE INDEX idx_claim_object_entity_id ON claim(object_entity_id);
CREATE INDEX idx_claim_truth_status ON claim(truth_status);
CREATE INDEX idx_claim_snippet_id ON claim(snippet_id);
CREATE INDEX idx_claim_predicate ON claim(predicate);
```

#### `claim_contradiction`

Links contradictory claims together (supports DISPUTED status and enables graph visualization):

```sql
CREATE TABLE claim_contradiction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Two contradictory claims
    claim_a_id UUID NOT NULL REFERENCES claim(id) ON DELETE CASCADE,
    claim_b_id UUID NOT NULL REFERENCES claim(id) ON DELETE CASCADE,

    -- Metadata
    contradiction_reason TEXT,  -- Why we think they contradict
    confidence FLOAT DEFAULT 1.0,  -- 0-1 scale
    detected_by VARCHAR(50),  -- 'manual', 'heuristic', 'llm'

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_contradiction_claim_a ON claim_contradiction(claim_a_id);
CREATE INDEX idx_contradiction_claim_b ON claim_contradiction(claim_b_id);
```

#### `snippet_analysis` (extend Phase 1 design)

Stores analysis results for document snippets:

```sql
CREATE TABLE snippet_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Target
    world_id UUID NOT NULL REFERENCES world(id) ON DELETE CASCADE,
    snippet_id UUID NOT NULL REFERENCES document_snippet(id) ON DELETE CASCADE,

    -- Analysis results
    contradiction_score FLOAT,  -- 0-1 scale; 1.0 = highly contradictory with canon
    contains_claim_about_canon_entities BOOLEAN,
    analysis_notes TEXT,

    -- Metadata
    analyzed_by VARCHAR(50),  -- 'heuristic', 'llm', 'manual'

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_snippet_analysis_snippet_id ON snippet_analysis(snippet_id);
CREATE INDEX idx_snippet_analysis_world_id ON snippet_analysis(world_id);
```

### 3.2 Migration Strategy

Since Phase 1 already has a deployed schema, create a new migration file:

**File**: `lorekeeper/db/migrations/versions/002_add_claim_truth.py`

Use Alembic to:

1. Create the three new tables above
2. Add `entity_version` table (if not already present) for versioning support
3. Add indexes for performance

**Key Migration Considerations**:
- Preserve existing data (non-destructive)
- Make `claim` FK to `entity_version` optional (nullable) for Phase 2 MVP
- Run migration in test environment first
- Document rollback procedure

---

## 4. SQLAlchemy Models

### 4.1 New Python Models

Add to `lorekeeper/db/models.py`:

```python
# New enum for ClaimTruth
class ClaimTruth(str, Enum):
    """Truth value for a claim."""
    CANON_TRUE = "CANON_TRUE"
    CANON_FALSE = "CANON_FALSE"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"
    IN_WORLD_TRUE = "IN_WORLD_TRUE"

# Claim model
class Claim(Base):
    """Claim (atomic statement) model."""

    __tablename__ = "claim"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    snippet_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    # Subject-Predicate-Object triple
    subject_entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    predicate: Mapped[str] = mapped_column(String(255), nullable=False)
    object_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_entity_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    # Truth value
    truth_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ClaimTruth.UNKNOWN
    )

    # Audit trail
    canon_ref_entity_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Claim subject={self.subject_entity_id} {self.predicate} {self.object_text or self.object_entity_id} [{self.truth_status}]>"


# Contradiction model
class ClaimContradiction(Base):
    """Model linking contradictory claims."""

    __tablename__ = "claim_contradiction"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_a_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    claim_b_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    contradiction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)
    detected_by: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<ClaimContradiction a={self.claim_a_id} contradicts b={self.claim_b_id}>"


# Snippet analysis model
class SnippetAnalysis(Base):
    """Analysis results for snippets."""

    __tablename__ = "snippet_analysis"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    world_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    snippet_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    contradiction_score: Mapped[float | None] = mapped_column(nullable=True)
    contains_claim_about_canon_entities: Mapped[bool] = mapped_column(default=False)
    analysis_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    analyzed_by: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return f"<SnippetAnalysis snippet={self.snippet_id} contradiction_score={self.contradiction_score}>"
```

---

## 5. API Layer Changes

### 5.1 New Schemas (Pydantic Models)

Add to `lorekeeper/api/schemas.py`:

```python
# Enum for API responses
class ClaimTruthEnum(str, Enum):
    CANON_TRUE = "CANON_TRUE"
    CANON_FALSE = "CANON_FALSE"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"
    IN_WORLD_TRUE = "IN_WORLD_TRUE"

# Request/response schemas
class ClaimCreate(BaseModel):
    subject_entity_id: UUID | None = None
    predicate: str
    object_text: str | None = None
    object_entity_id: UUID | None = None
    truth_status: ClaimTruthEnum = ClaimTruthEnum.UNKNOWN
    snippet_id: UUID | None = None
    notes: str | None = None

class ClaimUpdate(BaseModel):
    truth_status: ClaimTruthEnum | None = None
    notes: str | None = None

class ClaimResponse(BaseModel):
    id: UUID
    world_id: UUID
    subject_entity_id: UUID | None
    predicate: str
    object_text: str | None
    object_entity_id: UUID | None
    truth_status: ClaimTruthEnum
    snippet_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClaimContradictionResponse(BaseModel):
    id: UUID
    claim_a_id: UUID
    claim_b_id: UUID
    contradiction_reason: str | None
    confidence: float
    detected_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SnippetAnalysisResponse(BaseModel):
    id: UUID
    snippet_id: UUID
    contradiction_score: float | None
    contains_claim_about_canon_entities: bool
    analysis_notes: str | None
    analyzed_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 5.2 New API Endpoints

Create `lorekeeper/api/routes/claims.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from lorekeeper.api.schemas import (
    ClaimCreate, ClaimUpdate, ClaimResponse, ClaimContradictionResponse, SnippetAnalysisResponse
)
from lorekeeper.db.models import Claim, ClaimTruth, World
from lorekeeper.db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/claims", tags=["claims"])

# CRUD endpoints
@router.post("", response_model=ClaimResponse)
def create_claim(world_id: UUID, claim_create: ClaimCreate, db: Session = Depends(get_db)):
    """Create a new claim."""
    world = db.query(World).filter(World.id == world_id).first()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    db_claim = Claim(world_id=world_id, **claim_create.model_dump())
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(world_id: UUID, claim_id: UUID, db: Session = Depends(get_db)):
    """Retrieve a specific claim."""
    claim = db.query(Claim).filter(
        Claim.id == claim_id, Claim.world_id == world_id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@router.patch("/{claim_id}", response_model=ClaimResponse)
def update_claim(
    world_id: UUID, claim_id: UUID, claim_update: ClaimUpdate, db: Session = Depends(get_db)
):
    """Update a claim's truth status or notes."""
    claim = db.query(Claim).filter(
        Claim.id == claim_id, Claim.world_id == world_id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    for key, value in claim_update.model_dump(exclude_unset=True).items():
        setattr(claim, key, value)

    db.commit()
    db.refresh(claim)
    return claim

@router.delete("/{claim_id}")
def delete_claim(world_id: UUID, claim_id: UUID, db: Session = Depends(get_db)):
    """Delete a claim."""
    claim = db.query(Claim).filter(
        Claim.id == claim_id, Claim.world_id == world_id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    db.delete(claim)
    db.commit()
    return {"message": "Claim deleted"}

# Search/filter endpoints
@router.get("", response_model=list[ClaimResponse])
def list_claims(
    world_id: UUID,
    entity_id: UUID | None = Query(None),
    truth_status: str | None = Query(None),
    predicate: str | None = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """List claims with optional filters."""
    query = db.query(Claim).filter(Claim.world_id == world_id)

    if entity_id:
        query = query.filter(Claim.subject_entity_id == entity_id)
    if truth_status:
        query = query.filter(Claim.truth_status == truth_status)
    if predicate:
        query = query.filter(Claim.predicate == predicate)

    return query.offset(skip).limit(limit).all()

# Contradiction endpoints
@router.post("/{claim_a_id}/contradicts/{claim_b_id}")
def link_contradiction(
    world_id: UUID, claim_a_id: UUID, claim_b_id: UUID, db: Session = Depends(get_db)
):
    """Link two claims as contradictory."""
    claim_a = db.query(Claim).filter(Claim.id == claim_a_id, Claim.world_id == world_id).first()
    claim_b = db.query(Claim).filter(Claim.id == claim_b_id, Claim.world_id == world_id).first()

    if not claim_a or not claim_b:
        raise HTTPException(status_code=404, detail="One or both claims not found")

    # Mark both as DISPUTED
    claim_a.truth_status = "DISPUTED"
    claim_b.truth_status = "DISPUTED"

    # Create contradiction link
    contradiction = ClaimContradiction(
        claim_a_id=claim_a_id,
        claim_b_id=claim_b_id,
        detected_by="manual"
    )

    db.add(contradiction)
    db.commit()

    return {"message": "Claims linked as contradictory"}

@router.get("/{claim_id}/contradictions", response_model=list[ClaimContradictionResponse])
def get_contradictions(world_id: UUID, claim_id: UUID, db: Session = Depends(get_db)):
    """Get all contradictions for a claim."""
    claim = db.query(Claim).filter(
        Claim.id == claim_id, Claim.world_id == world_id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Get all contradictions where this claim is either side
    contradictions = db.query(ClaimContradiction).filter(
        (ClaimContradiction.claim_a_id == claim_id) |
        (ClaimContradiction.claim_b_id == claim_id)
    ).all()

    return contradictions
```

Register in `lorekeeper/api/main.py`:

```python
from lorekeeper.api.routes import claims

app.include_router(claims.router)
```

---

## 6. Service Layer

### 6.1 Claim Extraction Service

Create `lorekeeper/api/services/claim_extractor.py`:

```python
"""
Service for extracting claims from document snippets.

This is the MVP implementation. Phase 3+ can add LLM-based extraction.
"""

from uuid import UUID
from sqlalchemy.orm import Session
from lorekeeper.db.models import Claim, ClaimTruth, EntityMention, DocumentSnippet

def extract_claims_from_snippet(
    snippet_id: UUID,
    world_id: UUID,
    db: Session,
    strategy: str = "mention_based"
) -> list[Claim]:
    """
    Extract claims from a snippet based on entity mentions.

    MVP strategy: For each entity mentioned in the snippet, create an UNKNOWN claim.
    Phase 3+: Use LLM to extract subject-predicate-object triples.
    """

    snippet = db.query(DocumentSnippet).filter(DocumentSnippet.id == snippet_id).first()
    if not snippet:
        return []

    if strategy == "mention_based":
        # Get all entity mentions in this snippet
        mentions = db.query(EntityMention).filter(EntityMention.snippet_id == snippet_id).all()

        claims = []
        for mention in mentions:
            # Create a generic "mentioned_in_document" claim
            claim = Claim(
                world_id=world_id,
                snippet_id=snippet_id,
                subject_entity_id=mention.entity_id,
                predicate="mentioned_in_document",
                object_text=snippet.snippet_text[:100],  # First 100 chars
                truth_status=ClaimTruth.UNKNOWN,
                notes=f"Extracted from entity mention: {mention.mention_text}"
            )
            claims.append(claim)

        db.add_all(claims)
        db.commit()
        return claims

    return []
```

---

## 7. Enhanced Retrieval Service

### 7.1 Update Retrieval Policies

Extend `lorekeeper/api/services/retrieval.py` to support truth status filtering:

```python
class RetrievalPolicy(str, Enum):
    """Retrieval policy (existing)."""
    STRICT_ONLY = "STRICT_ONLY"
    MYTHIC_ONLY = "MYTHIC_ONLY"
    HYBRID = "HYBRID"
    # NEW:
    CANON_TRUE_ONLY = "CANON_TRUE_ONLY"  # Only canonically verified facts
    NO_CANON_FALSE = "NO_CANON_FALSE"    # Everything except known false
    IN_WORLD_BELIEFS = "IN_WORLD_BELIEFS"  # What NPCs believe (IN_WORLD_TRUE + CANON_TRUE)

def retrieve_lore(
    query: str,
    world_id: UUID,
    policy: RetrievalPolicy,
    top_k: int = 12,
    filters: dict | None = None,
    db: Session = Depends(get_db),
) -> RetrievalResponse:
    """Enhanced retrieval supporting claim-based filtering."""

    # ... existing vector search logic ...

    # NEW: Filter snippets by associated claim truth status
    if policy == "CANON_TRUE_ONLY":
        # Only return snippets where all associated claims are CANON_TRUE
        valid_snippets = (
            db.query(DocumentSnippet)
            .join(Claim, Claim.snippet_id == DocumentSnippet.id)
            .filter(Claim.truth_status == "CANON_TRUE")
            .all()
        )

    elif policy == "NO_CANON_FALSE":
        # Exclude snippets with CANON_FALSE claims
        invalid_snippets = (
            db.query(DocumentSnippet)
            .join(Claim, Claim.snippet_id == DocumentSnippet.id)
            .filter(Claim.truth_status == "CANON_FALSE")
            .all()
        )
        valid_snippets = [s for s in all_snippets if s not in invalid_snippets]

    elif policy == "IN_WORLD_BELIEFS":
        # Show what's widely believed
        valid_snippets = (
            db.query(DocumentSnippet)
            .join(Claim, Claim.snippet_id == DocumentSnippet.id)
            .filter(
                (Claim.truth_status == "IN_WORLD_TRUE") |
                (Claim.truth_status == "CANON_TRUE")
            )
            .all()
        )

    # ... continue with ranking and response building ...
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

Create `lorekeeper/tests/test_claims.py`:

```python
import pytest
from uuid import uuid4
from datetime import datetime
from lorekeeper.db.models import Claim, ClaimTruth, World, Entity
from lorekeeper.api.schemas import ClaimCreate, ClaimTruthEnum

def test_create_claim_canon_true(db_session, world_id, entity_id):
    """Test creating a CANON_TRUE claim."""
    claim = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="died_in",
        object_text="Year 1032",
        truth_status=ClaimTruth.CANON_TRUE
    )
    db_session.add(claim)
    db_session.commit()

    retrieved = db_session.query(Claim).filter(Claim.id == claim.id).first()
    assert retrieved.truth_status == ClaimTruth.CANON_TRUE
    assert retrieved.predicate == "died_in"

def test_create_contradiction(db_session, world_id, entity_id):
    """Test creating two contradictory claims."""
    claim_a = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="is_alive",
        truth_status=ClaimTruth.CANON_FALSE
    )
    claim_b = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="is_alive",
        truth_status=ClaimTruth.CANON_TRUE
    )

    db_session.add_all([claim_a, claim_b])
    db_session.commit()

    # Create contradiction
    contradiction = ClaimContradiction(
        claim_a_id=claim_a.id,
        claim_b_id=claim_b.id,
        contradiction_reason="Direct contradiction on alive status"
    )
    db_session.add(contradiction)
    db_session.commit()

    # Mark both as DISPUTED
    claim_a.truth_status = ClaimTruth.DISPUTED
    claim_b.truth_status = ClaimTruth.DISPUTED
    db_session.commit()

    retrieved = db_session.query(ClaimContradiction).filter(
        ClaimContradiction.claim_a_id == claim_a.id
    ).first()
    assert retrieved.contradiction_reason is not None

def test_list_claims_by_truth_status(db_session, world_id, entity_id):
    """Test filtering claims by truth status."""
    # Create multiple claims with different truth statuses
    for truth_status in [ClaimTruth.CANON_TRUE, ClaimTruth.CANON_TRUE,
                        ClaimTruth.UNKNOWN, ClaimTruth.IN_WORLD_TRUE]:
        claim = Claim(
            world_id=world_id,
            subject_entity_id=entity_id,
            predicate=f"predicate_{truth_status}",
            truth_status=truth_status
        )
        db_session.add(claim)
    db_session.commit()

    canon_true_claims = db_session.query(Claim).filter(
        Claim.world_id == world_id,
        Claim.truth_status == ClaimTruth.CANON_TRUE
    ).all()

    assert len(canon_true_claims) == 2

def test_in_world_true_vs_canon_false(db_session, world_id, entity_id):
    """Test that IN_WORLD_TRUE and CANON_FALSE are distinct."""
    # This claim is canonically false but widely believed
    claim = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="is_magical",
        truth_status=ClaimTruth.IN_WORLD_TRUE,
        notes="Everyone believes it, but it's false"
    )
    db_session.add(claim)
    db_session.commit()

    retrieved = db_session.query(Claim).filter(Claim.id == claim.id).first()
    assert retrieved.truth_status == ClaimTruth.IN_WORLD_TRUE
    # This allows NPC behavior: "NPCs believe this" vs "it's actually true"
```

### 8.2 Integration Tests

Create `lorekeeper/tests/test_claim_endpoints.py`:

```python
def test_post_claim_endpoint(client, world_id):
    """Test creating a claim via API."""
    response = client.post(
        f"/worlds/{world_id}/claims",
        json={
            "subject_entity_id": str(entity_id),
            "predicate": "died_in",
            "object_text": "Year 1032",
            "truth_status": "CANON_TRUE"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["truth_status"] == "CANON_TRUE"

def test_get_claims_filtered(client, world_id):
    """Test retrieving claims with filters."""
    response = client.get(
        f"/worlds/{world_id}/claims",
        params={"truth_status": "CANON_TRUE"}
    )
    assert response.status_code == 200
    claims = response.json()
    assert all(c["truth_status"] == "CANON_TRUE" for c in claims)

def test_link_contradiction_endpoint(client, world_id, claim_a_id, claim_b_id):
    """Test linking contradictory claims."""
    response = client.post(
        f"/worlds/{world_id}/claims/{claim_a_id}/contradicts/{claim_b_id}"
    )
    assert response.status_code == 200
```

### 8.3 Acceptance Tests

```python
def test_claim_truth_workflow(db_session, client, world_id, entity_id):
    """
    Acceptance test: Create facts, rumors, contradictions, resolve disputes.

    Scenario:
    1. King Aldren is canonical (entity exists)
    2. Claim: CANON_TRUE - Aldren died in 1032
    3. Claim: CANON_FALSE - Aldren is still alive
    4. Claim: UNKNOWN - Aldren's treasure is hidden in the lake
    5. Mythic rumor: IN_WORLD_TRUE - "Everyone says Aldren rules from beneath the lake"
    """

    # 1. Create canonical entity
    entity = db_session.query(Entity).filter(Entity.id == entity_id).first()
    assert entity is not None

    # 2. Create canon truth claim
    claim_died = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="died_in",
        object_text="Year 1032",
        truth_status=ClaimTruth.CANON_TRUE
    )
    db_session.add(claim_died)
    db_session.commit()

    # 3. Create contradictory claim (false)
    claim_alive = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="is_alive",
        truth_status=ClaimTruth.CANON_FALSE
    )
    db_session.add(claim_alive)
    db_session.commit()

    # 4. Create unknown claim
    claim_treasure = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="has_treasure_in_lake",
        truth_status=ClaimTruth.UNKNOWN
    )
    db_session.add(claim_treasure)
    db_session.commit()

    # 5. Create in-world-true claim (mythic but widely believed)
    claim_myth = Claim(
        world_id=world_id,
        subject_entity_id=entity_id,
        predicate="rules_from_beneath_lake",
        truth_status=ClaimTruth.IN_WORLD_TRUE,
        notes="Widely believed in mythology; canonically false but culturally significant"
    )
    db_session.add(claim_myth)
    db_session.commit()

    # Test retrieval by truth status
    canon_true = db_session.query(Claim).filter(
        Claim.world_id == world_id,
        Claim.truth_status == ClaimTruth.CANON_TRUE
    ).all()
    assert len(canon_true) == 1
    assert canon_true[0].predicate == "died_in"

    # Test in-world-true for NPC knowledge bases
    npc_beliefs = db_session.query(Claim).filter(
        Claim.world_id == world_id,
        Claim.truth_status.in_([ClaimTruth.IN_WORLD_TRUE, ClaimTruth.CANON_TRUE])
    ).all()
    assert len(npc_beliefs) >= 2
```

---

## 9. Implementation Roadmap

### Phase 2a: Foundation (Week 1)

- [x] Design data model and schemas
- [ ] Create database migration (`002_add_claim_truth.py`)
- [ ] Implement SQLAlchemy models
- [ ] Add Pydantic schemas
- [ ] Unit tests for models

**Deliverable**: Database schema ready, models testable

### Phase 2b: API Endpoints (Week 2)

- [ ] Implement CRUD endpoints
- [ ] Implement filtering/search endpoints
- [ ] Implement contradiction linking
- [ ] Integration tests for endpoints
- [ ] Register routes in main app

**Deliverable**: All claim endpoints working

### Phase 2c: Services & Extraction (Week 3)

- [ ] Implement claim extraction service (MVP: mention-based)
- [ ] Enhance retrieval service with truth-status filtering
- [ ] Add new retrieval policies (CANON_TRUE_ONLY, etc.)
- [ ] Service-level tests

**Deliverable**: Claims extractable, retrieval policy working

### Phase 2d: Polish & Documentation (Week 4)

- [ ] Comprehensive test suite (all acceptance tests passing)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Database schema documentation
- [ ] Usage examples
- [ ] Migration rollback procedure

**Deliverable**: Production-ready Phase 2

---

## 10. Integration Points

### 10.1 Agentic Pipeline (Phase 3)

When integrating with the book generation pipeline:

1. **Extraction**: After documents are indexed, extract claims from snippets
2. **Verification**: Run claims against canonical entities
3. **Feedback**: Mark claims as CANON_TRUE/FALSE/UNKNOWN/DISPUTED/IN_WORLD_TRUE
4. **Retrieval**: Use appropriate policy based on narrative needs
5. **Generation**: Pass claim context to LLM for consistent writing

### 10.2 NPC Knowledge Bases (Phase 3+)

```python
class NPCKnowledgeBase:
    """What an NPC knows/believes."""
    npc_id: UUID
    known_truths: list[Claim]  # CANON_TRUE claims NPC has learned
    believed_myths: list[Claim]  # IN_WORLD_TRUE claims NPC believes
    false_beliefs: list[Claim]  # CANON_FALSE claims NPC mistakenly believes

    def what_does_npc_know(self) -> list[Claim]:
        return self.known_truths + self.believed_myths + self.false_beliefs
```

### 10.3 Contradiction Detection (Phase 3+)

When adding automated contradiction detection:

```python
class ContradictionDetector:
    """Detects contradictions between claims."""

    def detect_contradictions(self, claim: Claim, db: Session) -> list[Claim]:
        """Find all claims that contradict this one."""
        # Could be LLM-based, heuristic, or rule-based
        # Returns list of contradictory claims
        # Creates ClaimContradiction records with confidence scores
```

---

## 11. Open Questions for Phase 2+

1. **Claim Extraction Strategy**: Should we support LLM-based extraction in Phase 2, or keep it manual/heuristic?
   - Recommendation: Keep MVP as mention-based; add LLM extraction in Phase 3

2. **Entity Versioning**: Should claims reference specific entity versions?
   - Recommendation: Make it optional in Phase 2; phase in strict versioning later

3. **Predicate Standardization**: Should we have a fixed set of predicates, or free-form?
   - Recommendation: Start free-form; add ontology in Phase 3 if needed

4. **Contradiction Confidence**: How confident should we be before marking as DISPUTED?
   - Recommendation: Phase 2 = manual; Phase 3+ = add confidence scoring

5. **Performance at Scale**: How many claims per world?
   - Recommendation: Phase 2 assumes <100k claims; monitor and optimize indices if needed

---

## 12. Success Criteria

### Phase 2 Completion

- ✅ All CRUD operations on claims working
- ✅ Claim extraction from snippets working (mention-based MVP)
- ✅ Contradiction linking working
- ✅ Retrieval policies (CANON_TRUE_ONLY, etc.) working
- ✅ All integration tests passing
- ✅ API documented (OpenAPI)
- ✅ Database migration tested and reversible
- ✅ Zero regressions in Phase 1 functionality

### Downstream Readiness (Phase 3)

- ✅ Agentic pipeline can query claims by truth status
- ✅ NPC knowledge bases can be built from claims
- ✅ Contradiction detection can plug into service layer

---

## 13. References

- Phase 1 README: Section 3.2 (Claim table design)
- Phase 1 README: Section 4.2 (Response contract)
- Phase 1 README: Section 8.1 (Soft contradiction flagging)
- existing `entity_mention` table: shows how to link snippets to entities

---

## Appendix: Example SQL for Seeding

```sql
-- Create test world
INSERT INTO world (id, name, description) VALUES
  (gen_random_uuid(), 'Aldren Kingdom', 'Test world with canonical king');

-- Create canonical entity
INSERT INTO entity (id, world_id, type, canonical_name, summary) VALUES
  (gen_random_uuid(), [world_id], 'Character', 'King Aldren', 'The late King of Aldren');

-- Create CANON_TRUE claim
INSERT INTO claim (id, world_id, subject_entity_id, predicate, object_text, truth_status) VALUES
  (gen_random_uuid(), [world_id], [entity_id], 'died_in', 'Year 1032', 'CANON_TRUE');

-- Create CANON_FALSE claim
INSERT INTO claim (id, world_id, subject_entity_id, predicate, truth_status, notes) VALUES
  (gen_random_uuid(), [world_id], [entity_id], 'is_alive', 'CANON_FALSE', 'Contradicts death claim');

-- Create IN_WORLD_TRUE claim
INSERT INTO claim (id, world_id, subject_entity_id, predicate, truth_status, notes) VALUES
  (gen_random_uuid(), [world_id], [entity_id], 'rules_from_beneath_lake', 'IN_WORLD_TRUE',
   'Widely believed myth; canonically false');
```
