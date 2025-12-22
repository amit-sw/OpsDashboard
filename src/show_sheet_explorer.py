import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def _build_drive_client(service_account_info):
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)


@st.cache_data(ttl=600)
def _fetch_sheet_metadata(_service_account_info):
    service_account_info=_service_account_info
    drive = _build_drive_client(service_account_info)
    filters = ["mimeType = 'application/vnd.google-apps.spreadsheet'"]
    folder_id = service_account_info.get("folder_id")
    if folder_id:
        filters.append(f"'{folder_id}' in parents")
    query = " and ".join(filters)

    files = []
    page_token = None
    while True:
        response = (
            drive.files()
            .list(
                q=query,
                pageSize=200,
                fields="nextPageToken, files(id, name, webViewLink, owners(displayName), modifiedTime)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                orderBy="modifiedTime desc",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    normalized = []
    for f in files:
        owners = f.get("owners") or [{}]
        normalized.append(
            {
                "name": f.get("name") or "Untitled sheet",
                "owner": owners[0].get("displayName") or "Unknown",
                "modifiedTime": f.get("modifiedTime"),
                "open_link": f.get("webViewLink")
                or f"https://docs.google.com/spreadsheets/d/{f.get('id')}/edit",
            }
        )
    return normalized


def _format_timestamp(ts: str | None) -> str:
    if not ts:
        return "Unknown"
    try:
        return pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts


def show_sheet_explorer():
    st.title("Sheet Explorer")
    service_account_info = st.secrets.get("gdrive_secrets", {})
    if not service_account_info:
        st.error("Google Drive service account secrets are missing (gdrive_secrets).")
        return

    with st.sidebar:
        st.subheader("Sheet Explorer Filters")
        search_term = st.text_input("Sheet name contains").strip().lower()
        refresh = st.button("Refresh sheet list", key="refresh_sheet_explorer")

    if refresh:
        _fetch_sheet_metadata.clear()

    try:
        sheets = _fetch_sheet_metadata(service_account_info)
    except HttpError as exc:
        st.error(f"Failed to load sheets from Google Drive: {exc}")
        return
    except Exception as exc:
        st.error(f"Unexpected error while loading sheets: {exc}")
        return

    filtered = []
    for sheet in sheets:
        name = sheet["name"].lower()
        if search_term and search_term not in name:
            continue
        filtered.append(sheet)

    if not filtered:
        st.info("No Google Sheets matched your filters.")
        return

    df = pd.DataFrame(
        {
            "Sheet Name": [item["name"] for item in filtered],
            "Last Modified": [_format_timestamp(item["modifiedTime"]) for item in filtered],
            "Open Sheet": [item["open_link"] for item in filtered],
        }
    )

    st.caption(f"Showing {len(df)} Google Sheets currently accessible to this service account.")
    st.data_editor(
        df,
        column_config={
            "Open Sheet": st.column_config.LinkColumn("Open Sheet", display_text="Open")
        },
        hide_index=True,
        use_container_width=True,
        disabled=True,
    )
