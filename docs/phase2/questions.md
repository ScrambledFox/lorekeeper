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
  -> Yes, there should be canon "ground truths" that are established facts in the lore base. However, there can also be "disputed accounts" that are not necessarily false, but are not universally accepted as true. The pipeline should be able to distinguish between these two types of information and handle them accordingly.
- Should the API reject inconsistent content, flag it for review, or allow it with warnings?
-> The API should reject inconsistent content and return an error message indicating the inconsistency. However, if the inconsistency is minor or can be explained by the perspective of the in-lore writer, the API can allow it with a warning.

## 3. Document Generation Scope

- What size range are we talking? (e.g., paragraph-length entries vs. multi-chapter tomes?)
-> The size of the documents can vary greatly depending on the type of document being generated. For example, a journal entry may be a few paragraphs long, while an academic paper or historical record may be several pages or even chapters long. Books can be multi-chapter tomes ranging to dozens or even hundreds of pages.
- Should the pipeline generate multiple document types? (journals, academic papers, historical records, myths, etc.)
-> The pipeline should be able to generate a variety of document types, including but not limited to journals, academic papers, historical records, myths, legends, propaganda, and more. The size of the documents can vary greatly depending on the type of document being generated. For example, a journal entry may be a few paragraphs long, while an academic paper or historical record may be several pages or even chapters long.
- Can the in-lore writer reference or cite existing documents?
-> Yes, but the references don't always have to be accurate. For example, an in-lore writer may reference a document that doesn't exist, or misquote a document. This can add to the depth and complexity of the lore base.

## 4. Current LoreKeeper State

- Do you have an existing API/database structure I should build upon?
- What's the current tech stack? (backend framework, database, LLM provider, etc.)
- Is there existing document storage/retrieval?
-> LoreKeeper is the document storage/retrieval system. It uses FastAPI for the backend framework, SQLAlchemy for database interactions, and an async PostgreSQL database. The LLM provider is not specified, but the system is designed to be LLM-agnostic, allowing for integration with various LLM providers as needed.

## 5. In-Lore Writer Definition

- Should writers be configurable entities with defined traits? (e.g., "Merlin: Neutral Good, Archmage, tends toward obscure knowledge, aims to enlighten but sometimes misleads for greater good")
-> Yes, writers should be configurable entities with defined traits. This will help the pipeline generate content that is consistent with the writer's perspective, knowledge, and biases.
- Can writers have conflicting goals or viewpoints that the pipeline needs to navigate?
-> Yes, this is an important aspect of creating a rich and dynamic lore base. The pipeline should be able to navigate conflicting goals and viewpoints, and generate content that reflects these complexities.
