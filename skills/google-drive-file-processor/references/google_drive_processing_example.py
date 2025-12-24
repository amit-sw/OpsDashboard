"""Drop-in helpers for connecting to Google Drive and exporting files by MIME type.

These routines are copied from OpsDashboard's `utils/process_gsheets.py` so you can
embed them in any project by importing this file from the skill package.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/presentations.readonly",
]

MIME_EXPORT_TARGETS: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pptx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    ),
    "application/vnd.google-apps.drawing": ("application/pdf", "pdf"),
    "application/vnd.google-apps.site": ("application/pdf", "pdf"),
}


def build_drive_clients(service_account_info: dict) -> dict:
    """Return Drive, Sheets, and Slides API clients backed by the same credentials."""
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return {
        "drive": build("drive", "v3", credentials=creds),
        "sheets": build("sheets", "v4", credentials=creds),
        "slides": build("slides", "v1", credentials=creds),
    }


def iterate_drive_files(
    drive_client,
    *,
    folder_id: Optional[str] = None,
    mime_filters: Optional[List[str]] = None,
) -> Iterator[dict]:
    """Yield Drive file payloads within an optional folder and MIME subset."""
    filters: List[str] = []
    if folder_id:
        filters.append(f"'{folder_id}' in parents")
    if mime_filters:
        quoted = ", ".join(f"'{mime}'" for mime in mime_filters)
        filters.append(f"mimeType in ({quoted})")
    query = " and ".join(filters) if filters else None

    page_token = None
    while True:
        response = (
            drive_client.files()
            .list(
                q=query,
                pageSize=200,
                fields="nextPageToken, files(id, name, mimeType)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                pageToken=page_token,
            )
            .execute()
        )
        for record in response.get("files", []):
            yield record
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def _download_request(request) -> bytes:
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def save_binary_file(drive_client, file_id: str, destination: Path) -> Path:
    """Download any non-Google file (PDF, XLSX, etc.) to `destination`."""
    payload = _download_request(drive_client.files().get_media(fileId=file_id))
    destination.write_bytes(payload)
    return destination


def export_google_file(
    drive_client,
    file_id: str,
    *,
    target_mime: str,
    suffix: str,
    destination: Path,
) -> Path:
    """Export a Google Doc/Sheet/Slide/etc. into a standard format."""
    payload = _download_request(
        drive_client.files().export_media(fileId=file_id, mimeType=target_mime)
    )
    target = destination.with_suffix(f".{suffix}")
    target.write_bytes(payload)
    return target


def read_google_sheet(
    sheets_client,
    spreadsheet_id: str,
    *,
    cell_range: Optional[str] = None,
) -> Dict[str, List[List[str]]]:
    """Return the workbook as {sheet_title: rows}."""
    workbook = (
        sheets_client.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    )
    data: Dict[str, List[List[str]]] = {}
    for sheet in workbook.get("sheets", []):
        title = sheet.get("properties", {}).get("title")
        if not title:
            continue
        range_name = f"{title}!{cell_range}" if cell_range else title
        response = (
            sheets_client.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        data[title] = response.get("values", [])
    return data


def sheet_rows_to_dataframe(rows: List[List[str]]) -> pd.DataFrame:
    """Convert a 2D values list into a pandas.DataFrame (assumes header row)."""
    if not rows:
        return pd.DataFrame()
    header, *body = rows
    return pd.DataFrame(body, columns=header)


def read_google_slides(slides_client, presentation_id: str) -> List[str]:
    """Return a flat list of text runs found within the presentation."""
    presentation = (
        slides_client.presentations().get(presentationId=presentation_id).execute()
    )
    lines: List[str] = []
    for slide in presentation.get("slides", []):
        for element in slide.get("pageElements", []):
            shape = element.get("shape")
            if not shape:
                continue
            for text_element in shape.get("text", {}).get("textElements", []):
                run = text_element.get("textRun", {})
                content = (run.get("content") or "").strip()
                if content:
                    lines.append(content)
    return lines


def process_drive_file(
    clients: dict,
    file_payload: dict,
    output_dir: Path,
) -> dict:
    """Route a Drive file to the appropriate handler based on MIME type."""
    drive_client = clients["drive"]
    sheets_client = clients.get("sheets")
    slides_client = clients.get("slides")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_id = file_payload["id"]
    name = file_payload["name"]
    mime = file_payload["mimeType"]
    artifact_base = output_dir / name

    result: dict = {
        "id": file_id,
        "name": name,
        "mimeType": mime,
        "kind": "binary",
        "artifact": None,
        "metadata": {},
    }

    if mime == "application/vnd.google-apps.spreadsheet" and sheets_client:
        sheet_rows = read_google_sheet(sheets_client, file_id)
        frames = {tab: sheet_rows_to_dataframe(rows) for tab, rows in sheet_rows.items()}
        result["kind"] = "sheet"
        result["metadata"] = {"rows": sheet_rows, "dataframes": frames}
        return result

    if mime == "application/vnd.google-apps.presentation" and slides_client:
        result["kind"] = "slides"
        result["metadata"] = {"lines": read_google_slides(slides_client, file_id)}
        return result

    if mime == "application/vnd.google-apps.form":
        result["kind"] = "form"
        result["metadata"] = {
            "warning": "Google Forms responses cannot be downloaded via Drive API."
        }
        return result

    if mime.startswith("application/vnd.google-apps."):
        export_mime, suffix = MIME_EXPORT_TARGETS.get(
            mime, ("application/pdf", "pdf")
        )
        result["kind"] = "export"
        result["artifact"] = str(
            export_google_file(
                drive_client,
                file_id,
                target_mime=export_mime,
                suffix=suffix,
                destination=artifact_base,
            )
        )
        return result

    result["artifact"] = str(save_binary_file(drive_client, file_id, artifact_base))
    return result


def process_drive_folder(
    service_account_info: dict,
    *,
    folder_id: Optional[str],
    output_dir: Path,
) -> List[dict]:
    """Convenience wrapper that builds clients and processes every file in a folder."""
    clients = build_drive_clients(service_account_info)
    results: List[dict] = []
    for file_payload in iterate_drive_files(clients["drive"], folder_id=folder_id):
        results.append(process_drive_file(clients, file_payload, output_dir))
    return results


def fetch_sheet_tables(
    service_account_info: dict,
    sheet_ids: Iterable[str],
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """Load multiple Google Sheets into a {sheet_id: {tab: dataframe}} mapping."""
    clients = build_drive_clients(service_account_info)
    sheets_client = clients["sheets"]
    aggregated: Dict[str, Dict[str, pd.DataFrame]] = {}
    for sheet_id in sheet_ids:
        rows = read_google_sheet(sheets_client, sheet_id)
        aggregated[sheet_id] = {
            tab: sheet_rows_to_dataframe(tab_rows) for tab, tab_rows in rows.items()
        }
    return aggregated
