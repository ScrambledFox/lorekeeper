Below is a Phase 1 implementation plan for **LoreKeeper** (the lore/knowledge store) designed to support both:

* **Strict lore**: canonical “ground truth” facts used for consistency.
* **Mythic lore**: in-world stories, rumors, religious texts, propaganda, and intentionally false accounts that may reference strict entities but are not necessarily true.

This plan is written so another LLM (or engineer) can begin executing immediately.

---

# Phase 1 Implementation Plan: LoreKeeper

## 0) Phase 1 goals and non-goals

### Goals

1. Store and retrieve **canonical entities/facts** (strict lore).
2. Store and retrieve **mythic narratives** (stories, rumors, scriptures, songs, apocrypha) that can:

   * reference strict entities,
   * contradict strict facts,
   * contradict each other,
   * and be intentionally fabricated in-world.
3. Support **similarity search** across both strict and mythic sources.
4. Provide **citation-grade retrieval**: every returned snippet has a stable ID and provenance.
5. Provide an API surface that the agentic writing pipeline can use without direct DB coupling.

### Non-goals (Phase 1)

* Full graph DB relationships and complex reasoning (can come Phase 2).
* Multi-user collaboration workflows and UI (minimal admin endpoints only).
* Automated contradiction resolution (Phase 1 detects/flags; resolution is manual or deferred).

---

# 1) Recommended tech choices (Phase 1)

* **Postgres** as the system of record.
* **pgvector** for embeddings and semantic search.
* **FastAPI** (or NestJS) for API; examples below assume FastAPI.
* **Object storage** optional in Phase 1; store narrative text in Postgres first (fine for MVP).

Why: This yields one operationally simple deployment, with strong retrieval.

---

# 2) Core concept: “Truth model” and provenance

You need a single, explicit model that lets strict and mythic coexist.

## 2.1 Lore objects

In Phase 1, store two kinds of objects:

1. **Entity** (strict, canonical):

* People, places, factions, artifacts, deities, events, etc.
* Has structured fields and short/long descriptions.

2. **Document** (mythic or strict source text):

* In-world texts (chronicles, hymns, tavern tales, propaganda).
* Also system sources (previous books generated, GM notes, “historian commentary”).
* Documents produce **snippets** for retrieval + citation.

### Key rule

**Truth is not stored only as text.** Canonical truth lives in Entities (and optional structured facts). Documents are “claims” that may be true/false/unknown.

---

# 3) Data model (Phase 1 schema)

Below is a concrete schema suitable for immediate implementation.

## 3.1 Enums

* `lore_mode`: `STRICT`, `MYTHIC`
* `doc_kind`: `CHRONICLE`, `SCRIPTURE`, `BALLAD`, `RUMOR`, `PROPAGANDA`, `MEMOIR`, `TEXTBOOK`, `BESTIARY`, `GM_NOTES`, `SYSTEM_OUTPUT`, `OTHER`
* `claim_truth`: `CANON_TRUE`, `CANON_FALSE`, `UNKNOWN`, `DISPUTED`, `IN_WORLD_TRUE`
  (Explanation: “IN_WORLD_TRUE” means widely believed in-setting, regardless of canon.)

## 3.2 Tables

### `world`

* `id` UUID PK
* `name` text
* `description` text
* `created_at`, `updated_at`

### `canon_snapshot`

* `id` UUID PK
* `world_id` FK
* `label` text (e.g., `v0.1.0`)
* `created_at`
* Notes: Phase 1 can create snapshots as “tags” for entity versions.

### `entity`

* `id` UUID PK
* `world_id` FK
* `type` text (Character, Location, Faction, Deity, Event, Artifact, Culture, etc.)
* `canonical_name` text
* `aliases` text[] default []
* `summary` text
* `description` text
* `tags` text[] default []
* `status` text default `ACTIVE` (or enum)
* `created_at`, `updated_at`

### `entity_version`

* `id` UUID PK
* `entity_id` FK
* `snapshot_id` FK nullable (if you only snapshot periodically)
* `version_num` int
* `data_json` jsonb (complete entity representation at that version)
* `change_note` text
* `created_at`

Phase 1 shortcut: you can omit `entity_version` initially and implement snapshots later; but having it early is valuable.

### `document`

* `id` UUID PK
* `world_id` FK
* `mode` lore_mode (STRICT or MYTHIC)
  (STRICT documents can be “official records,” mythic documents are stories/rumors.)
* `kind` doc_kind
* `title` text
* `author` text nullable (in-world author)
* `in_world_date` text nullable (freeform for fantasy calendars)
* `provenance` jsonb (source tool, uploader, seed, etc.)
* `text` text (full text, Phase 1)
* `created_at`, `updated_at`

### `document_snippet`

* `id` UUID PK
* `document_id` FK
* `world_id` FK (denormalized)
* `snippet_index` int
* `start_char` int
* `end_char` int
* `snippet_text` text
* `embedding` vector
* `created_at`

Snippet design: chunk documents into 300–800 tokens with overlap.

### `entity_mention`

(links mythic/strict texts to strict entities)

* `id` UUID PK
* `snippet_id` FK
* `entity_id` FK
* `mention_text` text
* `confidence` float (0–1)
* `created_at`

Phase 1: populate this with best-effort extraction (LLM-based or rules) but allow it to be empty.

### `claim`

(optional but recommended even in Phase 1; enables mythic “false stories” cleanly)

* `id` UUID PK
* `world_id` FK
* `snippet_id` FK
* `subject_entity_id` FK nullable
* `predicate` text (e.g., “died_on”, “founded”, “ruled”, “battled”, “is_parent_of”)
* `object_text` text nullable (freeform)
* `object_entity_id` FK nullable
* `truth_status` claim_truth
* `canon_ref_entity_version_id` FK nullable (if claim evaluated against a canon version)
* `notes` text
* `created_at`

Phase 1: you can skip claim extraction initially and still achieve mythic mode via documents alone. But adding this table early makes later contradiction tooling straightforward.

---

# 4) Retrieval behavior: strict vs mythic

Your writing pipeline will query LoreKeeper with a “retrieval policy.” Implement these policies in Phase 1:

## 4.1 Query policies

* `STRICT_ONLY`: return entities + snippets where `document.mode=STRICT`
* `MYTHIC_ONLY`: return snippets where `document.mode=MYTHIC`
* `HYBRID`: return both, but label clearly and rank strict higher unless user requests legends

## 4.2 Response contract

Every retrieval result must include:

* `object_type`: `ENTITY` or `SNIPPET`
* Stable IDs: `entity_id` or `snippet_id`
* Provenance: document title, kind, author, mode
* A “reliability label”:

  * strict entity: `CANON`
  * strict document snippet: `CANON_SOURCE`
  * mythic snippet: `MYTHIC_SOURCE`
* Optional: linked entity mentions

This enables downstream LLM prompting: “You may cite CANON as fact; you may present MYTHIC as rumor/legend.”

---

# 5) API specification (Phase 1)

Implement a small set of endpoints. Keep them stable.

## 5.1 World endpoints

* `POST /worlds`
* `GET /worlds/{world_id}`

## 5.2 Entity endpoints

* `POST /worlds/{world_id}/entities`
* `GET /worlds/{world_id}/entities/{entity_id}`
* `POST /worlds/{world_id}/entities/search` (keyword + filters)
* `PATCH /worlds/{world_id}/entities/{entity_id}`

Entity create/update should accept:

* `type`, `canonical_name`, `aliases`, `summary`, `description`, `tags`

## 5.3 Document endpoints

* `POST /worlds/{world_id}/documents`

  * body: `mode`, `kind`, `title`, `author`, `in_world_date`, `text`, `provenance`
* `GET /worlds/{world_id}/documents/{doc_id}`
* `POST /worlds/{world_id}/documents/{doc_id}/index`

  * chunks document into snippets, computes embeddings, stores in `document_snippet`
* `POST /worlds/{world_id}/documents/search`

  * keyword search in titles/authors/kind

## 5.4 Retrieval endpoint (key)

* `POST /worlds/{world_id}/retrieve`

  * request:

    * `query` (string)
    * `policy` (`STRICT_ONLY`|`MYTHIC_ONLY`|`HYBRID`)
    * `top_k` (e.g., 12)
    * `filters`: kinds, tags, entity types, timeframe (optional)
    * `include_entities` boolean
    * `include_snippets` boolean
  * response:

    * `entities`: list of entity cards
    * `snippets`: list of snippet cards (with provenance + mode)
    * `debug`: optional scores

## 5.5 Mention linking endpoint (optional)

* `POST /worlds/{world_id}/snippets/{snippet_id}/link_entities`

  * Phase 1: can be manual linking or automated.

---

# 6) Indexing pipeline (how to create embeddings + chunks)

Implement a deterministic indexer.

## 6.1 Chunking rules

* Split by paragraphs where possible.
* Target 300–800 tokens per chunk (depending on model).
* Overlap 10–15% to preserve continuity.
* Store `start_char/end_char` for stable citations.

## 6.2 Embeddings

* Use one embedding model for Phase 1 (consistent dimensions).
* Store vectors in `document_snippet.embedding`.

## 6.3 Entity embeddings (optional but useful)

Optionally create an `entity_embedding` table:

* embed `canonical_name + aliases + summary + description`
  This makes entity retrieval much better.

---

# 7) How strict and mythic interact (the critical design)

You want mythic stories about strict entities without contaminating canon.

## 7.1 Authoritative canon rule

* Canonical facts come from `entity` (and later `entity_version`), not from mythic documents.
* Mythic documents can reference entities via `entity_mention`, but that does not update canon.

## 7.2 “Fake stories about real people/places”

This is exactly what mythic documents are for:

* Example: a rumor that “Duke Rhalos is a dragon in disguise.”

  * Store as a `document` with mode=MYTHIC, kind=RUMOR.
  * Optionally extract a `claim` with truth_status `CANON_FALSE` (if canon says he isn’t) or `UNKNOWN`.

## 7.3 “Gods” and “uncertain metaphysics”

Decide per world whether deities are canonical beings or mythic constructs:

* If deities are “real” in your setting: represent them as `entity(type=Deity)` in strict canon.
* If deities are ambiguous: keep them as mythic documents only, or create entity entries with tags like `metaphysical_uncertain`.

Phase 1 should support both with tags; do not over-engineer.

---

# 8) Minimal contradiction support (Phase 1)

Phase 1 should at least **flag** contradictions without resolving them.

## 8.1 Soft contradiction flagging (MVP)

When retrieving in HYBRID:

* If a mythic snippet mentions an entity and contains strong contradictory language (“actually alive”, “secretly”, “never happened”), label it as `POTENTIAL_CONTRADICTION`.

Implementation approach:

* Simple heuristic + optional LLM classifier:

  * Input: strict entity summary + snippet text
  * Output: {contradiction_likelihood: 0..1, notes}

Store results in a table if needed:

* `snippet_analysis(snippet_id, contradiction_score, extracted_entities, updated_at)`

---

# 9) Phase 1 execution steps (milestones)

## Milestone A: Project skeleton

1. Repo structure:

   * `lorekeeper/api` (FastAPI)
   * `lorekeeper/db` (migrations)
   * `lorekeeper/indexer` (chunking + embedding)
   * `lorekeeper/tests`
2. Add Docker compose:

   * Postgres + pgvector
   * API container

## Milestone B: Database + migrations

1. Create tables: `world`, `entity`, `document`, `document_snippet`
2. Add `vector` column + index for similarity search.
3. Seed script: create one world.

## Milestone C: Core APIs

1. Implement world create/get.
2. Implement entity CRUD + basic search.
3. Implement document create/get.
4. Implement document indexing endpoint:

   * chunk
   * embed
   * insert snippets

## Milestone D: Retrieval endpoint

1. Implement vector search over `document_snippet`:

   * filter by `world_id`
   * join `document` to filter by mode/kind
2. Implement optional entity retrieval:

   * keyword match + optional entity embeddings later
3. Return combined results with explicit labels and provenance.

## Milestone E: Mythic support polish

1. Ensure documents have `mode` and `kind`.
2. Add “in-world author/date” fields and return them in retrieval.
3. Add a small set of example mythic docs:

   * scripture excerpt
   * tavern rumor
   * conflicting chronicle paragraph

## Milestone F: Optional entity mentions

1. Add `entity_mention` table.
2. Provide an endpoint to manually link mentions.
3. (Optional) automated linking:

   * string match on canonical name/aliases
   * later: LLM-based NER + disambiguation

Deliverable for Phase 1: a working service where the book pipeline can call `/retrieve` and get canon facts and mythic rumors separately or together.

---

# 9.1) Critical Domain Questions (Phase 2+ Planning)

As you progress beyond Phase 1, the following questions will determine scope and architecture for Phase 2 and beyond. These represent decision points that will significantly impact design:

## Question 1: Entity Relationships

**Do you need entity relationships?** (e.g., "Location has ruler Entity", "Character is parent of Character")

* **Current state**: Entities are isolated atoms. No structural relationships modeled.
* **Workaround**: Encode relationships in description or tags (e.g., "current_ruler:King_Aldren_id").
* **Phase 2 implication**:
  * If YES: Add `entity_relationship` table with relationship type, source_entity, target_entity.
  * Enable graph queries: "Find all people who rule Location X" or "Show family tree of House Y".
  * Support validation: "Verify no cycles in parent_of relationships".
* **Impact**: Graph reasoner, query optimization, entity embedding adjustments.

## Question 2: Automated Contradiction Detection

**Do you want automated contradiction detection?**

* **Current state**: Not implemented. Manual process via HYBRID retrieval.
* **Approach**: After retrieval, you manually review STRICT vs MYTHIC results and flag conflicts.
* **Phase 2 implication**:
  * If YES: Implement semantic reasoning layer.
  * Add `contradiction_detector` service (heuristic or LLM-based).
  * Populate `snippet_analysis` or `claim` table with contradiction scores.
  * Enable queries: "Show all claims contradicting canon entity X".
* **Impact**: LLM integration, contradiction resolution workflows, human review UIs.

## Question 3: Entity Versioning / Audit Trail

**Do you need entity versioning and update history?**

* **Current state**: Entities are immutable once created (by design). No change log.
* **Why immutable**: Prevents breaking citations in generated books.
* **Phase 2 implication**:
  * If YES: Implement `entity_version` table (already designed in schema section 3.2).
  * Support "entity as of version X", rollback, change approval workflows.
  * Track what changed, when, and by whom.
  * Enable: "Show how King Aldren's description evolved across v0.1, v0.2, v0.3".
* **Impact**: Backwards compatibility strategy, versioned snippet references, migration tooling.

## Question 4: Explicit Truth Value Tracking

**Should snippets/claims have explicit "is_true" fields?**

* **Current state**: Truth is inferred from document mode (STRICT vs MYTHIC).
  * STRICT snippets → assumed true (CANON_SOURCE).
  * MYTHIC snippets → narratives of unknown truth (MYTHIC_SOURCE).
* **Gap**: You cannot explicitly mark a MYTHIC snippet as "known false" or "in-world consensus".
* **Phase 2 implication**:
  * If YES: Add `claim_truth` enum to `claim` or `snippet_analysis` table.
  * Values: `CANON_TRUE`, `CANON_FALSE`, `UNKNOWN`, `DISPUTED`, `IN_WORLD_TRUE`.
  * Enable retrieval filters: "Show only CANON_TRUE facts" or "Show what NPCs believe (IN_WORLD_TRUE)".
* **Impact**: Semantic differentiation, NPC knowledge bases, reader vs character POV.

## Question 5: Direct Document-Entity Relationships

**Should documents link to specific entities they're about?**

* **Current state**: Documents are free-form text. Entity linking happens via:
  * Document → Snippet → EntityMention → Entity (3 hops).
* **Why indirect**: Allows snippets to mention multiple entities, supports contradiction scenarios.
* **Phase 2 implication**:
  * If YES: Add `document_entity` join table (optional, denormalized for performance).
  * Fast query: "What documents mention King Aldren?"
  * Support document-level entity tags: "This document is primarily about X and secondarily about Y".
* **Impact**: Query performance, retrieval ranking, document summaries.

## Question 6: Integration with Agentic Pipeline

**How will LoreKeeper integrate with your writing agents?**

* **Current state**: API is ready for agent calls, but no documented agent contract.
* **Phase 2 implication**:
  * If agents are stateful: LoreKeeper needs session/context management.
  * If agents need to create entities/documents: add write validation, approval workflows.
  * If agents need multi-turn reasoning: add retrieval caching, conversation context.
  * Define strict prompt contracts (see section 10: "Prompting contract").
* **Impact**: Agent framework choice, prompt engineering, feedback loops.

---



# 10) “Prompting contract” for downstream LLMs (critical context)

Define a standard instruction the writing agents will follow when using LoreKeeper outputs.

**Rule set to give the writing LLM:**

* Anything labeled `CANON` may be stated as fact.
* Anything labeled `MYTHIC_SOURCE` must be framed as legend/rumor/scripture, with attribution.
* If a mythic snippet contradicts canon, present it as contested (“some claim…”) unless the user asked for unreliable narration.
* Always cite snippet IDs (or document+snippet IDs) when using retrieved text.

This contract prevents mythic content from silently becoming “true” in generated books.

---

# 11) Acceptance tests (Phase 1)

Create automated tests (even minimal) that prove strict vs mythic works.

1. Insert strict entity: “King Aldren” died in 1032.
2. Insert mythic rumor document: “Aldren still lives beneath the lake.”
3. Query HYBRID for “Aldren lake”

   * result contains:

     * the entity card (CANON)
     * the rumor snippet (MYTHIC_SOURCE)
4. Query STRICT_ONLY

   * rumor snippet excluded
5. Query MYTHIC_ONLY

   * entity card optional (depending on include_entities), rumor included

---

# 12) Implementation notes (decisions to lock early)

1. **IDs are sacred**: never change snippet IDs once referenced in a book.
2. **Chunk determinism**: if you re-index, preserve old snippets or version documents to avoid breaking citations.
3. **Mythic is first-class**: treat it as content with provenance, not “noise.”
