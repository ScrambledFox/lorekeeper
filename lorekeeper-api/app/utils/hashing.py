"""Hashing and canonicalization utilities for asset jobs."""

import hashlib
import json
from typing import Any
from uuid import UUID


def canonicalize_value(value: Any) -> str:
    """Convert a value to its canonical string representation."""
    if isinstance(value, UUID):
        return str(value)
    elif isinstance(value, dict):
        # Sort keys and recursively canonicalize
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    elif isinstance(value, (list, tuple)):
        # Recursively canonicalize list items
        return json.dumps(
            [canonicalize_value(item) for item in value],
            separators=(",", ":"),
        )
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    else:
        return str(value)


def canonicalize_prompt_spec(prompt_spec: dict) -> str:
    """Canonicalize a prompt spec to a stable JSON representation."""
    return json.dumps(prompt_spec, sort_keys=True, separators=(",", ":"), default=str)


def canonicalize_references(
    world_id: UUID,
    asset_type: str,
    provider: str,
    model_id: str | None,
    claim_ids: list[UUID],
    entity_ids: list[UUID],
    source_chunk_ids: list[UUID],
    source_id: UUID | None,
) -> str:
    """Canonicalize lore references to a stable string."""
    refs = {
        "world_id": str(world_id),
        "asset_type": asset_type,
        "provider": provider,
        "model_id": model_id,
        "claim_ids": sorted([str(cid) for cid in claim_ids]),
        "entity_ids": sorted([str(eid) for eid in entity_ids]),
        "source_chunk_ids": sorted([str(scid) for scid in source_chunk_ids]),
        "source_id": str(source_id) if source_id else None,
    }
    return json.dumps(refs, sort_keys=True, separators=(",", ":"))


def canonicalize_lore_snapshot(
    claim_ids: list[UUID],
    entity_ids: list[UUID],
    source_chunk_ids: list[UUID],
    claim_updates: dict[str, str] | None = None,
    entity_updates: dict[str, str] | None = None,
    source_chunk_updates: dict[str, str] | None = None,
) -> str:
    """Canonicalize a lore snapshot (including update timestamps) to a stable string."""
    snapshot = {
        "claims": {
            str(cid): claim_updates.get(str(cid), "") if claim_updates else "" for cid in claim_ids
        },
        "entities": {
            str(eid): entity_updates.get(str(eid), "") if entity_updates else ""
            for eid in entity_ids
        },
        "source_chunks": {
            str(scid): source_chunk_updates.get(str(scid), "") if source_chunk_updates else ""
            for scid in source_chunk_ids
        },
    }
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"))


def compute_input_hash(
    prompt_spec: dict,
    world_id: UUID,
    asset_type: str,
    provider: str,
    model_id: str | None,
    claim_ids: list[UUID],
    entity_ids: list[UUID],
    source_chunk_ids: list[UUID],
    source_id: UUID | None,
    claim_updates: dict[str, str] | None = None,
    entity_updates: dict[str, str] | None = None,
    source_chunk_updates: dict[str, str] | None = None,
) -> str:
    """
    Compute a stable SHA256 hash for input idempotency.

    This hash is based on:
    1. Canonical JSON serialization of prompt_spec
    2. Sorted IDs of references
    3. World ID, asset type, provider, and model ID
    4. Optional lore snapshot (for drift prevention)
    """
    # Canonicalize each component
    prompt_canonical = canonicalize_prompt_spec(prompt_spec)
    refs_canonical = canonicalize_references(
        world_id, asset_type, provider, model_id, claim_ids, entity_ids, source_chunk_ids, source_id
    )
    snapshot_canonical = canonicalize_lore_snapshot(
        claim_ids, entity_ids, source_chunk_ids, claim_updates, entity_updates, source_chunk_updates
    )

    # Concatenate all canonicalized components
    combined = f"{prompt_canonical}|{refs_canonical}|{snapshot_canonical}"

    # Compute SHA256 hash
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def extract_uuids_from_references(
    references: dict,
) -> tuple[list[UUID], list[UUID], list[UUID], UUID | None]:
    """Extract and sort UUID lists from references dict."""
    claim_ids = [
        UUID(cid) if isinstance(cid, str) else cid for cid in references.get("claim_ids", [])
    ]
    entity_ids = [
        UUID(eid) if isinstance(eid, str) else eid for eid in references.get("entity_ids", [])
    ]
    source_chunk_ids = [
        UUID(scid) if isinstance(scid, str) else scid
        for scid in references.get("source_chunk_ids", [])
    ]
    source_id = None
    if references.get("source_id"):
        source_id = (
            UUID(references["source_id"])
            if isinstance(references["source_id"], str)
            else references["source_id"]
        )

    return claim_ids, entity_ids, source_chunk_ids, source_id
