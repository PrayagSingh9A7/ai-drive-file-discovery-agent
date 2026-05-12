import json
import logging
import os
from datetime import datetime
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from .config import Settings, get_settings


logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DEFAULT_FIELDS = (
    "nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink, webContentLink, "
    "iconLink, thumbnailLink, size)"
)


class DriveSearchInput(BaseModel):
    query: str = Field(..., description="Google Drive API q expression without folder restriction.")
    page_size: int | None = Field(default=None, ge=1, le=100)


class DriveFile(BaseModel):
    id: str
    name: str
    mimeType: str
    modifiedTime: str | None = None
    webViewLink: str | None = None
    webContentLink: str | None = None
    iconLink: str | None = None
    thumbnailLink: str | None = None
    size: str | None = None


def escape_drive_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def combine_with_folder_restriction(user_query: str, folder_id: str) -> str:
    folder_clause = f"'{escape_drive_literal(folder_id)}' in parents"
    base_clauses = [folder_clause, "trashed = false"]
    clean_query = (user_query or "").strip()

    if clean_query:
        return " and ".join([*base_clauses, f"({clean_query})"])

    return " and ".join(base_clauses)


def normalize_modified_time(value: str | None) -> str | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return value


class GoogleDriveClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._service: Any | None = None

    @property
    def service(self) -> Any:
        if self._service is None:

            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

            if not service_account_json:
                raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is missing.")

            service_account_info = json.loads(service_account_json)

            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=DRIVE_SCOPES,
            )

            self._service = build(
                "drive",
                "v3",
                credentials=credentials,
                cache_discovery=False,
            )

        return self._service

    def search_files(self, query: str, page_size: int | None = None) -> dict[str, Any]:
        if not self.settings.google_drive_folder_id:
            raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID is not configured.")

        restricted_query = combine_with_folder_restriction(
            query,
            self.settings.google_drive_folder_id,
        )

        page_limit = page_size or self.settings.drive_page_size

        files: list[dict[str, Any]] = []
        next_page_token: str | None = None
        pages_fetched = 0

        try:
            while pages_fetched < self.settings.drive_max_pages:
                response = (
                    self.service.files()
                    .list(
                        q=restricted_query,
                        spaces="drive",
                        fields=DEFAULT_FIELDS,
                        pageSize=page_limit,
                        pageToken=next_page_token,
                        orderBy="modifiedTime desc",
                    )
                    .execute()
                )

                files.extend(response.get("files", []))

                next_page_token = response.get("nextPageToken")

                pages_fetched += 1

                if not next_page_token:
                    break

        except HttpError as exc:
            logger.exception("Google Drive API search failed")
            details = getattr(exc, "error_details", None) or str(exc)
            raise RuntimeError(f"Google Drive search failed: {details}") from exc

        normalized_files = [
            DriveFile(
                id=item.get("id", ""),
                name=item.get("name", "Untitled"),
                mimeType=item.get("mimeType", "unknown"),
                modifiedTime=normalize_modified_time(item.get("modifiedTime")),
                webViewLink=item.get("webViewLink"),
                webContentLink=item.get("webContentLink"),
                iconLink=item.get("iconLink"),
                thumbnailLink=item.get("thumbnailLink"),
                size=item.get("size"),
            ).model_dump()
            for item in files
        ]

        return {
            "query": restricted_query,
            "results": normalized_files,
            "count": len(normalized_files),
            "has_more": bool(next_page_token),
        }


class DriveSearchTool(BaseTool):
    name: str = "drive_search"

    description: str = (
        "Search files in the configured Google Drive folder. "
        "Input must be a valid Google Drive API q query fragment."
    )

    args_schema: type[BaseModel] = DriveSearchInput

    _client: GoogleDriveClient = PrivateAttr()

    def __init__(self, client: GoogleDriveClient | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client = client or GoogleDriveClient()

    def _run(self, query: str, page_size: int | None = None) -> dict[str, Any]:
        return self._client.search_files(query=query, page_size=page_size)

    async def _arun(self, query: str, page_size: int | None = None) -> dict[str, Any]:
        return self._run(query=query, page_size=page_size)