# LoreKeeper Phase 2: Agentic AI Pipeline - Clarification Questions

## 1. In-Lore Writer Perspective & Reliability

- When Merlin writes about the Stone of Resurrection, should the pipeline understand that Merlin might have incomplete knowledge, biases, or intentionally mislead?
-> Yes, definitely, the pipeline should account for the perspective and reliability of the in-lore writer. If the in-lore writer is known to be unreliable or biased, the generated content should reflect that. This way, in-lore propoganda, myths, and legends can be created that add depth to the world.
- How does the system track "unreliable narrator" aspects? Should it maintain metadata about writer credibility/bias?
-> The system should use the 'entities' as sources of absolute truth. Of course, the generator of text can introduce bias, lies, unreliable information, etc.

## 2. Lore Consistency Checking

- What constitutes a "consistency check"? For example:
  - Does new content contradict existing established facts?
  -> New content that are True in their claims AND contradicts established facts should be flagged, as we want to maintain a consistent lore base. However, of course documents don't have to be checked against every established fact, as some documents may be myths or legends that are not meant to be factual. Or they may be written from a biased perspective, or from writers that have different information and knowledge from their perspective.
  - Does it contradict other in-lore writers' accounts (which might be acceptable)?
  -> This is acceptable, as different in-lore writers may have different perspectives, knowledge, and biases.
  - Are there canon "ground truths" vs. "disputed accounts"?
- Should the API reject inconsistent content, flag it for review, or allow it with warnings?

## 3. Document Generation Scope

- What size range are we talking? (e.g., paragraph-length entries vs. multi-chapter tomes?)
- Should the pipeline generate multiple document types? (journals, academic papers, historical records, myths, etc.)
- Can the in-lore writer reference or cite existing documents?

## 4. Current LoreKeeper State

- Do you have an existing API/database structure I should build upon?
- What's the current tech stack? (backend framework, database, LLM provider, etc.)
- Is there existing document storage/retrieval?

## 5. In-Lore Writer Definition

- Should writers be configurable entities with defined traits? (e.g., "Merlin: Neutral Good, Archmage, tends toward obscure knowledge")
- Can writers have conflicting goals or viewpoints that the pipeline needs to navigate?
