"""S3/Object Storage client and utilities for asset uploads/downloads."""

from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import InternalServerErrorException


class S3Client:
    """Client for interacting with S3-compatible object storage."""

    def __init__(self):
        """Initialize S3 client with configured credentials."""
        self.s3_client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self.expiry_seconds = settings.S3_PRESIGNED_URL_EXPIRY_SECONDS

    def generate_download_presigned_url(self, object_key: str) -> str:
        """
        Generate a presigned URL for downloading an object from S3.

        Args:
            object_key: The S3 key/path of the object

        Returns:
            Presigned URL valid for configured expiry time

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=self.expiry_seconds,
            )
            return url
        except ClientError as e:
            raise InternalServerErrorException(
                message=f"Failed to generate download presigned URL: {str(e)}"
            ) from e

    def generate_upload_presigned_url(
        self, object_key: str, content_type: str | None = None
    ) -> str:
        """
        Generate a presigned URL for uploading an object to S3.

        Args:
            object_key: The S3 key/path where object will be stored
            content_type: Optional MIME type of the object

        Returns:
            Presigned URL valid for configured expiry time

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        try:
            params = {"Bucket": self.bucket_name, "Key": object_key}
            if content_type:
                params["ContentType"] = content_type

            url = self.s3_client.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=self.expiry_seconds,
            )
            return url
        except ClientError as e:
            raise InternalServerErrorException(
                message=f"Failed to generate upload presigned URL: {str(e)}"
            ) from e

    def generate_multipart_upload_presigned_urls(
        self, object_key: str, part_count: int, content_type: str | None = None
    ) -> dict:
        """
        Generate presigned URLs for multipart upload (for large files).

        Args:
            object_key: The S3 key/path where object will be stored
            part_count: Number of parts to upload
            content_type: Optional MIME type of the object

        Returns:
            Dict with 'upload_id' and 'parts' list containing presigned URLs

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        try:
            # Initiate multipart upload
            params = {"Bucket": self.bucket_name, "Key": object_key}
            if content_type:
                params["ContentType"] = content_type

            response = self.s3_client.create_multipart_upload(**params)
            upload_id = response["UploadId"]

            # Generate presigned URLs for each part
            part_urls = []
            for part_number in range(1, part_count + 1):
                url = self.s3_client.generate_presigned_url(
                    "upload_part",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": object_key,
                        "PartNumber": part_number,
                        "UploadId": upload_id,
                    },
                    ExpiresIn=self.expiry_seconds,
                )
                part_urls.append({"part_number": part_number, "url": url})

            return {
                "upload_id": upload_id,
                "parts": part_urls,
                "expires_at": datetime.utcnow() + timedelta(seconds=self.expiry_seconds),
            }
        except ClientError as e:
            raise InternalServerErrorException(
                message=f"Failed to initiate multipart upload: {str(e)}"
            ) from e

    def complete_multipart_upload(
        self, object_key: str, upload_id: str, part_etags: list[dict]
    ) -> str:
        """
        Complete a multipart upload.

        Args:
            object_key: The S3 key/path of the object
            upload_id: The upload ID from initiate_multipart_upload
            part_etags: List of dicts with 'part_number' and 'etag' keys

        Returns:
            The S3 location of the completed object

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        try:
            parts = [
                {"PartNumber": part["part_number"], "ETag": part["etag"]} for part in part_etags
            ]

            response = self.s3_client.complete_multipart_upload(
                Bucket=self.bucket_name,
                Key=object_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )

            return response["Location"]
        except ClientError as e:
            raise InternalServerErrorException(
                message=f"Failed to complete multipart upload: {str(e)}"
            ) from e

    def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        """
        Abort a multipart upload.

        Args:
            object_key: The S3 key/path of the object
            upload_id: The upload ID to abort

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        try:
            self.s3_client.abort_multipart_upload(
                Bucket=self.bucket_name,
                Key=object_key,
                UploadId=upload_id,
            )
        except ClientError as e:
            raise InternalServerErrorException(
                message=f"Failed to abort multipart upload: {str(e)}"
            ) from e

    def head_object(self, object_key: str) -> dict | None:
        """
        Get metadata about an object without downloading it.

        Args:
            object_key: The S3 key/path of the object

        Returns:
            Metadata dict or None if object doesn't exist

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
            return {
                "size_bytes": response.get("ContentLength"),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            raise InternalServerErrorException(
                message=f"Failed to get object metadata: {str(e)}"
            ) from e

    def delete_object(self, object_key: str) -> None:
        """
        Delete an object from S3.

        Args:
            object_key: The S3 key/path of the object to delete

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
        except ClientError as e:
            raise InternalServerErrorException(message=f"Failed to delete object: {str(e)}") from e

    def delete_objects(self, object_keys: list[str]) -> None:
        """
        Delete multiple objects from S3.

        Args:
            object_keys: List of S3 keys/paths to delete

        Raises:
            InternalServerErrorException: If S3 operation fails
        """
        if not object_keys:
            return

        try:
            delete_requests = [{"Key": key} for key in object_keys]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={"Objects": delete_requests},
            )
        except ClientError as e:
            raise InternalServerErrorException(message=f"Failed to delete objects: {str(e)}") from e


# Singleton instance
_s3_client: S3Client | None = None


def get_s3_client() -> S3Client:
    """Get or create the S3 client singleton."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client
