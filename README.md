# OpsDashboard

Initial project scaffold for the OpsDashboard application. The repository currently provides:

- `app.py` as the runnable entry point.
- `src/` for core application modules (to be implemented).
- `test/` for automated tests.
- `doc/` for user-facing documentation.

Some key files:
- `utils/calendar_integration.py` exposes `CalendarClient` for Google Calendar access.
- `utils/supabase_integration.py` exposes `SupabaseClient` for database access.
- `utils/posthog_integration.py` will centralize PostHog analytics helpers.
- `src/core_utils.py` provides shared helpers such as query-parameter normalization for Streamlit pages.
- `src/show_pdf_upload.py` streams uploaded PDFs through `pdf_bytes_to_text(...)` so the extracted content can be reviewed inside the Streamlit UI.
- `src/show_table_explorer.py` surfaces the Supabase Table Explorer page that all authenticated roles (except guests) can use to browse live data.

## Testing

Install dependencies with `pip install -r requirements.txt` and run `pytest` to execute the automated checks. The `test/` suite now covers PDF upload handling alongside the existing utility tests.

Update this document as features and dependencies are added.

For DB managers:
1. Remember to add specific schema to Project->Settings->API to "Exposed Schemas" list
2. For all schema changes, please update helpders/create_schema.sql

Entry points:
* app.py: Main entry point
* app_yt_private_download.py: Streamlit app to download transcripts from private YouTube videos.
* test_app.py: Used for testing sub-functionality in isolation during development
* helpers/ : Code written for non-App use (e.g. loading specific tables)

For deveelopers:
1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. To run the main app: `streamlit run app.py`
5. To run the YouTube private video downloader:
   - Create a `client_secret.json` file in the root directory with your Google OAuth 2.0 credentials.
   - Run the app: `streamlit run app_yt_private_download.py`
   - The first authorization persists tokens at `.tokens/youtube.json`. Stored credentials are reused automatically until they expire; use the sidebar "Sign out" button to clear them manually.
   - Set `SUPABASE_URL` and `SUPABASE_KEY` environment variables (or add a `[supabase]` block in `secrets.toml`) to capture transcripts in the `youtube_private_videos` table. Each stored row includes the transcript segments with timing metadata inside the `transcript_segments` JSON column, a `transcript_downloaded_at` timestamp, and reruns only upload videos that have not been stored previously (videos are requested chronologically after the latest stored publish time).
   - Video discovery now relies on the YouTube `search.list` endpoint with the `forMine` flag to include private uploads while filtering results locally by the Channel you choose in the UI. This avoids the `channelId` + `forMine` API conflict that previously raised a `400 badRequest` error when fetching uploads.
   - When multiple channels are linked to the Google account, pick the desired channel in the dropdown before downloading transcripts; the selected channel filters the search results so you only pull transcripts for that brand channel.
   - If you see an “insufficient permission” warning, use the sidebar “Sign out” button and reauthorize; the app now requests the `youtube.force-ssl` scope to download captions from the YouTube Data API.


   We are keeping two sets of Google Credentials - one for Gmail, one for YT
