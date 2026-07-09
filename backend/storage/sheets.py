import json
import os
import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base import StorageBackend

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

MAX_RETRIES = 4


def _prefer_native_sheet(entries: list[dict]) -> dict[str, tuple[str, str]]:
    """When a native Google Sheet and an uploaded .xlsx share a base name,
    keep only the native Sheet - it's the one people actively edit."""
    by_base: dict[str, list[dict]] = {}
    for entry in entries:
        name = entry["name"].strip()
        base = name[:-5] if name.lower().endswith(".xlsx") else name
        by_base.setdefault(base.lower(), []).append(entry)

    result: dict[str, tuple[str, str]] = {}
    for base_key, group in by_base.items():
        sheets = [e for e in group if e["mimeType"] == SHEET_MIME]
        chosen = sheets or group
        if len(chosen) > 1:
            print(
                f"[SheetStorage] Ambiguous duplicate files for {base_key!r}: "
                f"{[e['name'] for e in chosen]!r} - keeping all"
            )
        for e in chosen:
            result[e["name"]] = (e["id"], e["mimeType"])
    return result


class SheetStorage(StorageBackend):
    """Mirrors the UGANDA/ local folder layout (root files + month subfolders)
    inside a single shared Google Drive folder. Each Google Sheet is exported
    as XLSX bytes on demand, so the existing pandas-based loaders work unchanged.
    """

    def __init__(self):
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if not creds_json:
            raise ValueError("GOOGLE_CREDENTIALS_JSON is not set in .env.")
        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID is not set in .env.")
        self._folder_id = folder_id

        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        self._drive = build("drive", "v3", credentials=creds, cache_discovery=False)

        # name -> id, for the month subfolders directly under the root folder
        self._dirs: dict[str, str] = {}
        # folder display name ("" for root) -> {filename: (file_id, mime_type)}
        self._files: dict[str, dict[str, tuple[str, str]]] = {}
        self.discover()

    # ── Drive API helpers ─────────────────────────────────────────────────

    def _list_children(self, folder_id: str) -> list[dict]:
        entries = []
        page_token = None
        while True:
            resp = self._with_retry(
                lambda: self._drive.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                )
                .execute()
            )
            entries.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return entries

    @staticmethod
    def _with_retry(call):
        attempt = 0
        while True:
            try:
                return call()
            except HttpError as e:
                status = getattr(e.resp, "status", None)
                if status in (429, 403) and attempt < MAX_RETRIES:
                    time.sleep(15 * (2 ** attempt))
                    attempt += 1
                    continue
                raise

    # ── Discovery ──────────────────────────────────────────────────────────

    def discover(self) -> None:
        """Rebuild the folder/file map from Drive. Cheap: one list call per
        folder (root + each month subfolder), no file content is fetched."""
        self._dirs = {}
        self._files = {}

        root_entries = self._list_children(self._folder_id)
        root_files = []
        for entry in root_entries:
            if entry["mimeType"] == FOLDER_MIME:
                self._dirs[entry["name"]] = entry["id"]
            elif entry["mimeType"] in (SHEET_MIME, XLSX_MIME):
                root_files.append(entry)
        self._files[""] = _prefer_native_sheet(root_files)

        for dir_name, dir_id in self._dirs.items():
            entries = [
                entry for entry in self._list_children(dir_id)
                if entry["mimeType"] in (SHEET_MIME, XLSX_MIME)
            ]
            self._files[dir_name] = _prefer_native_sheet(entries)

    # ── StorageBackend interface ────────────────────────────────────────────

    def get_file_bytes(self, relative_path: str) -> bytes:
        folder, _, fname = relative_path.rpartition("/")
        entry = self._files.get(folder, {}).get(fname)
        if not entry:
            raise FileNotFoundError(relative_path)
        file_id, mime_type = entry
        if mime_type == SHEET_MIME:
            # Native Google Sheet: export as XLSX
            return self._with_retry(
                lambda: self._drive.files()
                .export_media(fileId=file_id, mimeType=XLSX_MIME)
                .execute()
            )
        # Already an uploaded .xlsx file: download as-is
        return self._with_retry(
            lambda: self._drive.files().get_media(fileId=file_id).execute()
        )

    def list_files(self, folder: str) -> list[str]:
        return list(self._files.get(folder, {}).keys())

    def exists(self, relative_path: str) -> bool:
        folder, _, fname = relative_path.rpartition("/")
        return fname in self._files.get(folder, {})

    def list_dirs(self, folder: str = "") -> list[str]:
        if folder:
            return []
        return list(self._dirs.keys())
