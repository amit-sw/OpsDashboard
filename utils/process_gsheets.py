import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

import pandas as pd


# ====== HELPERS ======

def json_google_sheet(sheets_service, file_id, cell_range=None):
    """Return workbook contents as {sheet_title: rows}."""
    workbook = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
    data = {}
    for sheet in workbook.get('sheets', []):
        title = sheet.get('properties', {}).get('title')
        if not title:
            continue
        range_name = f"{title}!{cell_range}" if cell_range else title
        response = sheets_service.spreadsheets().values().get(
            spreadsheetId=file_id, range=range_name
        ).execute()
        data[title] = response.get('values', [])
    return data

def read_google_sheet(sheets_service,file_id, name="Name not provided"):
    """Read values from a Google Sheet."""
    print(f"\n🧮 Reading Google Sheet: {name}")
    sheets_data = json_google_sheet(sheets_service, file_id)

    for sheet_name, rows in sheets_data.items():
        print(f"\n-- {sheet_name} --")
        for row in rows:
            print(row)
    return sheets_data

def read_google_slides(slides_service, file_id, name):
    """Extract all text from a Google Slides presentation."""
    print(f"\n🎞️ Reading Google Slides: {name}")
    pres = slides_service.presentations().get(presentationId=file_id).execute()
    for i, slide in enumerate(pres.get('slides', []), start=1):
        print(f"\n--- Slide {i} ---")
        for el in slide.get('pageElements', []):
            shape = el.get('shape')
            if shape and 'text' in shape:
                for te in shape['text']['textElements']:
                    if 'textRun' in te:
                        txt = te['textRun']['content'].strip()
                        if txt:
                            print(txt)

def read_google_doc_or_export(file_id, name, mimeType, export_type, ext):
    """Export a Google Docs/Sheets/Slides file to standard format (e.g. .docx, .xlsx, .pptx, .pdf)."""
    print(f"\n⬇️ Exporting {name} ({mimeType}) to {ext}")
    request = drive_service.files().export_media(fileId=file_id, mimeType=export_type)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    with open(f"{name}.{ext}", 'wb') as f:
        f.write(fh.getbuffer())
    print(f"✅ Saved as {name}.{ext}")

def read_binary_file(file_id, name, mimeType):
    """Download non-Google binary files like PPTX, XLSX, PDF."""
    print(f"\n📥 Downloading binary file: {name}")
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    local_name = f"{name}"
    with open(local_name, 'wb') as f:
        f.write(fh.getbuffer())
    print(f"✅ Saved {local_name} ({mimeType})")

# ====== PROCESS FILES ======

def process_sheets(service_account_info, sheet_list):
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/presentations.readonly'
    ]

    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )
    sheets_service = build('sheets', 'v4', credentials=creds)
    results={}
    for sheet in sheet_list:
        res=read_google_sheet(sheets_service, sheet)
        results |= res
    return results


def get_info_gsheets(service_account_info, sheets_list):

    results = process_sheets(service_account_info, sheets_list)
    df_persons=pd.DataFrame()
    df_relations=pd.DataFrame()
    list_persons=results.get('persons')
    list_relations=results.get('relations')
    if list_persons:
        df_persons=pd.DataFrame(list_persons[1:],columns=list_persons[0])
    if list_relations:
        df_relations=pd.DataFrame(list_relations[1:],columns=list_relations[0])
    return df_persons, df_relations

def get_users_students(email, service_account_info, sheets_list):

    df_persons,df_relations=get_info_gsheets(service_account_info, sheets_list)

    person_names = set(df_persons.loc[df_persons['Email'].fillna('').str.strip().str.lower() == email,'Name'].astype(str))

    if not person_names:
        #st.info(f"Logged in user {email=} not found in Persons table")
        return None, df_persons,df_relations

    related_rows = df_relations[df_relations['Person'].astype(str).isin(person_names)]
    student_names = set(related_rows['Student'].astype(str))
    if not student_names:
        #st.info(f"Logged in user {email=}, {person_names=} not found in relationship table")
        return None, df_persons,df_relations

    filtered_df = df_persons[df_persons['Name'].astype(str).isin(student_names)]
    if filtered_df.empty:
        #st.info("No matching persons for related IDs.")
        return None, df_persons,df_relations
    #st.success("Related persons")

    return filtered_df, df_persons, df_relations


def process_files(service_account_info):
    # ====== SETUP ======
    SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/presentations.readonly'
    ]

    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )
    FOLDER_ID_PERSONS = service_account_info['folder_id']


    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    slides_service = build('slides', 'v1', credentials=creds)

    # ====== FETCH FILES ======
    query = f"'{FOLDER_ID_PERSONS}' in parents"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute()

    files = results.get('files', [])
    print(f"Found {len(files)} files in folder: {files}\n")

    for f in files:
        file_id = f['id']
        name = f['name']
        mimeType = f['mimeType']
        print(f"\n📄 {file_id} = {name}: {mimeType}")

        # --- Handle by type ---
        if mimeType == 'application/vnd.google-apps.spreadsheet':
            read_google_sheet(sheets_service, file_id, name)

        elif mimeType == 'application/vnd.google-apps.presentation':
            read_google_slides(slides_service, file_id, name)

        elif mimeType == 'application/vnd.google-apps.document':
            # Export Google Docs to .docx
            read_google_doc_or_export(
                file_id, name, mimeType,
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'docx'
            )

        elif mimeType == 'application/vnd.google-apps.form':
            print("⚠️ Google Forms cannot be read directly via API.")

        elif mimeType.startswith('application/vnd.google-apps'):
            # Generic catch-all for other Google file types
            read_google_doc_or_export(
                file_id, name, mimeType, 'application/pdf', 'pdf'
            )

        else:
            # Binary file (.pptx, .xlsx, .pdf, etc.)
            read_binary_file(file_id, name, mimeType)