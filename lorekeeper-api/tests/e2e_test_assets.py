#!/usr/bin/env python3
"""
End-to-end testing script for asset endpoints.

Tests the full asset lifecycle:
1. Create a world
2. Create entities and claims
3. Create asset jobs
4. Verify idempotency
5. Complete jobs with assets
6. List and retrieve assets
7. Generate presigned URLs
"""

import json
import sys
import time
import uuid
from datetime import datetime
from typing import Any

import httpx


BASE_URL = "http://localhost:8000"
USER_ID = "test-user-" + str(uuid.uuid4())[:8]
WORKER_TOKEN = "test-worker-token"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def log_section(title: str) -> None:
    print(f"\n{BLUE}{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}{RESET}\n")


def log_success(message: str) -> None:
    print(f"{GREEN}✓ {message}{RESET}")


def log_error(message: str) -> None:
    print(f"{RED}✗ {message}{RESET}")


def log_info(message: str) -> None:
    print(f"{YELLOW}ℹ {message}{RESET}")


def log_data(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


async def test_asset_workflow():
    """Run end-to-end asset workflow tests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Create a world
        log_section("Step 1: Creating a World")
        world_data = {
            "name": f"Test World {uuid.uuid4()}",
            "description": "A test world for asset testing",
        }
        world_response = await client.post(
            f"{BASE_URL}/worlds/",
            json=world_data,
            headers={"user-id": USER_ID},
        )
        if world_response.status_code != 201:
            log_error(f"Failed to create world: {world_response.text}")
            return

        world = world_response.json()
        world_id = world["id"]
        log_success(f"Created world: {world_id}")
        log_data(world)

        # Step 2: Create entities
        log_section("Step 2: Creating Entities")
        entities = []
        for i in range(2):
            entity_data = {
                "world_id": world_id,
                "name": f"Test Entity {i}",
                "entity_type": "character",
                "is_fiction": True,
            }
            entity_response = await client.post(
                f"{BASE_URL}/entities/",
                json=entity_data,
                headers={"user-id": USER_ID},
            )
            if entity_response.status_code != 201:
                log_error(f"Failed to create entity: {entity_response.text}")
                return

            entity = entity_response.json()
            entities.append(entity)
            log_success(f"Created entity: {entity['id']}")

        # Step 3: Create claims
        log_section("Step 3: Creating Claims")
        claims = []
        for i, entity in enumerate(entities):
            claim_data = {
                "world_id": world_id,
                "claim_text": f"Entity {i} has an interesting property",
                "belief_prevalence": 0.7,
                "truth_value": 0.8,
            }
            claim_response = await client.post(
                f"{BASE_URL}/claims/",
                json=claim_data,
                headers={"user-id": USER_ID},
            )
            if claim_response.status_code != 201:
                log_error(f"Failed to create claim: {claim_response.text}")
                return

            claim = claim_response.json()
            claims.append(claim)
            log_success(f"Created claim: {claim['id']}")

        # Step 4: Create first asset job
        log_section("Step 4: Creating Asset Job (Idempotent Test)")
        job_data = {
            "world_id": world_id,
            "asset_type": "video",
            "provider": "openai",
            "model_id": "gpt-4-turbo-preview",
            "priority": "normal",
            "prompt_spec": {
                "text": "Generate a promotional video",
                "duration_seconds": 30,
            },
            "references": {
                "entity_ids": [entities[0]["id"]],
                "claim_ids": [claims[0]["id"]],
            },
        }

        job_response_1 = await client.post(
            f"{BASE_URL}/assets/asset-jobs",
            json=job_data,
            headers={"user-id": USER_ID},
        )
        if job_response_1.status_code != 201:
            log_error(f"Failed to create asset job: {job_response_1.text}")
            return

        job_1 = job_response_1.json()
        job_id = job_1["id"]
        log_success(f"Created asset job: {job_id}")
        log_data({"id": job_id, "status": job_1["status"], "input_hash": job_1.get("input_hash")})

        # Step 5: Test idempotency - create same job again
        log_section("Step 5: Testing Idempotency")
        job_response_2 = await client.post(
            f"{BASE_URL}/assets/asset-jobs",
            json=job_data,
            headers={"user-id": USER_ID},
        )
        if job_response_2.status_code != 201:
            log_error(f"Failed to get idempotent job: {job_response_2.text}")
            return

        job_2 = job_response_2.json()
        if job_1["id"] == job_2["id"] and job_1["input_hash"] == job_2["input_hash"]:
            log_success("Idempotency works: Same job returned for identical request")
        else:
            log_error("Idempotency failed: Different job IDs returned")
            log_data({"job_1_id": job_1["id"], "job_2_id": job_2["id"]})

        # Step 6: Get asset job by ID
        log_section("Step 6: Retrieving Asset Job by ID")
        get_job_response = await client.get(
            f"{BASE_URL}/assets/asset-jobs/{job_id}",
            headers={"user-id": USER_ID},
        )
        if get_job_response.status_code != 200:
            log_error(f"Failed to get asset job: {get_job_response.text}")
            return

        retrieved_job = get_job_response.json()
        log_success(f"Retrieved asset job: {retrieved_job['id']}")
        log_data(
            {
                "id": retrieved_job["id"],
                "status": retrieved_job["status"],
                "world_id": retrieved_job["world_id"],
                "derivation": retrieved_job.get("derivation"),
            }
        )

        # Step 7: List asset jobs
        log_section("Step 7: Listing Asset Jobs")
        list_jobs_response = await client.get(
            f"{BASE_URL}/assets/asset-jobs?world_id={world_id}",
            headers={"user-id": USER_ID},
        )
        if list_jobs_response.status_code != 200:
            log_error(f"Failed to list asset jobs: {list_jobs_response.text}")
            return

        jobs_list = list_jobs_response.json()
        log_success(f"Retrieved {jobs_list['total']} asset job(s)")
        log_data(
            {
                "total": jobs_list["total"],
                "skip": jobs_list["skip"],
                "limit": jobs_list["limit"],
                "items_count": len(jobs_list["items"]),
            }
        )

        # Step 8: Update job status (worker operation)
        log_section("Step 8: Updating Job Status (Worker Operation)")
        status_update = {
            "status": "RUNNING",
            "started_at": datetime.utcnow().isoformat(),
        }
        update_response = await client.patch(
            f"{BASE_URL}/assets/asset-jobs/{job_id}",
            json=status_update,
            headers={
                "user-id": USER_ID,
                "Authorization": f"Bearer {WORKER_TOKEN}",
            },
        )
        if update_response.status_code != 200:
            log_error(f"Failed to update job status: {update_response.text}")
            return

        updated_job = update_response.json()
        log_success(f"Updated job status to: {updated_job['status']}")
        log_data({"id": updated_job["id"], "status": updated_job["status"]})

        # Step 9: Complete job with asset
        log_section("Step 9: Completing Job with Asset Data (Worker Operation)")
        asset_data = {
            "asset": {
                "world_id": world_id,
                "type": "video",
                "format": "mp4",
                "status": "ready",
                "storage_key": f"videos/{job_id}/output.mp4",
                "content_type": "video/mp4",
                "duration_seconds": 30,
                "size_bytes": 1024000,
                "checksum": "abc123def456",
                "meta": {"resolution": "1080p", "framerate": 30},
                "created_by": USER_ID,
            }
        }
        complete_response = await client.post(
            f"{BASE_URL}/assets/asset-jobs/{job_id}/complete",
            json=asset_data,
            headers={
                "user-id": USER_ID,
                "Authorization": f"Bearer {WORKER_TOKEN}",
            },
        )
        if complete_response.status_code != 200:
            log_error(f"Failed to complete job: {complete_response.text}")
            return

        completed_job = complete_response.json()
        asset_id = completed_job.get("asset", {}).get("id")
        log_success(f"Completed job with asset: {asset_id}")
        log_data(
            {
                "job_id": completed_job["id"],
                "job_status": completed_job["status"],
                "asset_id": asset_id,
            }
        )

        # Step 10: Get asset by ID
        if asset_id:
            log_section("Step 10: Retrieving Asset by ID")
            get_asset_response = await client.get(
                f"{BASE_URL}/assets/assets/{asset_id}",
                headers={"user-id": USER_ID},
            )
            if get_asset_response.status_code != 200:
                log_error(f"Failed to get asset: {get_asset_response.text}")
            else:
                asset = get_asset_response.json()
                log_success(f"Retrieved asset: {asset['id']}")
                log_data(
                    {
                        "id": asset["id"],
                        "type": asset["type"],
                        "format": asset["format"],
                        "storage_key": asset["storage_key"],
                    }
                )

            # Step 11: Generate presigned download URL
            log_section("Step 11: Generating Presigned Download URL")
            presign_response = await client.post(
                f"{BASE_URL}/assets/assets/{asset_id}/presign-download",
                headers={"user-id": USER_ID},
            )
            if presign_response.status_code != 200:
                log_error(f"Failed to generate presigned URL: {presign_response.text}")
            else:
                presign_data = presign_response.json()
                log_success("Generated presigned download URL")
                log_data(
                    {
                        "asset_id": presign_data.get("asset_id"),
                        "expires_at": presign_data.get("expires_at"),
                        "url_length": len(presign_data.get("presigned_url", "")),
                    }
                )

        # Step 12: List assets
        log_section("Step 12: Listing Assets")
        list_assets_response = await client.get(
            f"{BASE_URL}/assets/assets?world_id={world_id}",
            headers={"user-id": USER_ID},
        )
        if list_assets_response.status_code != 200:
            log_error(f"Failed to list assets: {list_assets_response.text}")
        else:
            assets_list = list_assets_response.json()
            log_success(f"Retrieved {assets_list['total']} asset(s)")
            log_data(
                {
                    "total": assets_list["total"],
                    "skip": assets_list["skip"],
                    "limit": assets_list["limit"],
                }
            )

        # Step 13: Test presigned upload URL
        log_section("Step 13: Generating Presigned Upload URL")
        upload_presign_data = {
            "world_id": world_id,
            "asset_type": "audio",
            "filename": "narration.mp3",
            "content_type": "audio/mpeg",
        }
        upload_presign_response = await client.post(
            f"{BASE_URL}/assets/assets/presign-upload",
            json=upload_presign_data,
            headers={"user-id": USER_ID},
        )
        if upload_presign_response.status_code != 200:
            log_error(f"Failed to generate upload presigned URL: {upload_presign_response.text}")
        else:
            upload_presign = upload_presign_response.json()
            log_success("Generated presigned upload URL")
            log_data(
                {
                    "expires_at": upload_presign.get("expires_at"),
                    "url_length": len(upload_presign.get("presigned_url", "")),
                }
            )

        # Step 14: Test job failure
        log_section("Step 14: Testing Job Failure Endpoint")
        # Create another job first
        job_data_2 = {
            "world_id": world_id,
            "asset_type": "audio",
            "provider": "elevenlabs",
            "model_id": "v1",
            "priority": "normal",
            "prompt_spec": {"text": "Generate audio narration"},
            "references": {
                "entity_ids": [entities[1]["id"]],
                "claim_ids": [claims[1]["id"]],
            },
        }
        job_response_3 = await client.post(
            f"{BASE_URL}/assets/asset-jobs",
            json=job_data_2,
            headers={"user-id": USER_ID},
        )
        if job_response_3.status_code != 201:
            log_error(f"Failed to create job for failure test: {job_response_3.text}")
        else:
            job_3 = job_response_3.json()
            job_id_3 = job_3["id"]

            fail_data = {
                "error_code": "GENERATION_FAILED",
                "error_message": "Audio generation service timed out",
            }
            fail_response = await client.post(
                f"{BASE_URL}/assets/asset-jobs/{job_id_3}/fail",
                json=fail_data,
                headers={
                    "user-id": USER_ID,
                    "Authorization": f"Bearer {WORKER_TOKEN}",
                },
            )
            if fail_response.status_code != 200:
                log_error(f"Failed to mark job as failed: {fail_response.text}")
            else:
                failed_job = fail_response.json()
                log_success(f"Job marked as failed: {failed_job['status']}")
                log_data(
                    {
                        "job_id": failed_job["id"],
                        "status": failed_job["status"],
                        "error_code": failed_job.get("error_code"),
                        "error_message": failed_job.get("error_message"),
                    }
                )

        log_section("All Tests Completed Successfully!")


async def inspect_database():
    """Inspect the PostgreSQL database directly using SQL."""
    import subprocess

    log_section("Database Inspection")

    # Docker exec into postgres container
    queries = [
        (
            "Tables in lorekeeper database",
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;",
        ),
        (
            "Asset Jobs",
            "SELECT id, world_id, status, provider, model_id, created_at FROM asset_jobs ORDER BY created_at DESC LIMIT 5;",
        ),
        (
            "Assets",
            "SELECT id, world_id, type, format, storage_key, created_at FROM assets ORDER BY created_at DESC LIMIT 5;",
        ),
        (
            "Asset Derivations",
            "SELECT id, asset_job_id, asset_id, input_hash FROM asset_derivations ORDER BY created_at DESC LIMIT 5;",
        ),
        (
            "Derivation References (Claims)",
            "SELECT derivation_id, claim_id FROM derivation_claims LIMIT 10;",
        ),
        (
            "Derivation References (Entities)",
            "SELECT derivation_id, entity_id FROM derivation_entities LIMIT 10;",
        ),
    ]

    for title, query in queries:
        print(f"\n{YELLOW}{title}:{RESET}")
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "lorekeeper_postgres",
                    "psql",
                    "-U",
                    "lorekeeper",
                    "-d",
                    "lorekeeper",
                    "-c",
                    query,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"Error: {result.stderr}")
        except Exception as e:
            print(f"Failed to execute query: {e}")


async def main():
    """Main test runner."""
    print(f"\n{BLUE}LoreKeeper Asset Endpoints E2E Test{RESET}")
    print(f"User ID: {USER_ID}")
    print(f"Base URL: {BASE_URL}\n")

    try:
        await test_asset_workflow()
        await inspect_database()
    except Exception as e:
        log_error(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
