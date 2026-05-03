# Data Flow

OpsDashboard moves data between Streamlit, Supabase, Google APIs, AWS, Braintree, AgentMail, and OpenAI-compatible LLM calls.

## Login and Authorization

1. User opens `app.py`.
2. Streamlit handles Google login through `st.login`.
3. The logged-in user's email is looked up in Supabase table `authorized_users`.
4. The user's role controls the navigation rendered by `src/verified_ui.py`.
5. Unknown users are treated as `guest`.

## Student and Relationship Data

1. Google service-account settings are read from `st.secrets["gdrive_secrets"]`.
2. `utils.process_gsheets.get_users_students(...)` loads configured sheets.
3. The app stores student, topic, person, and relationship data in `st.session_state`.
4. User-facing student pages use that session data and Supabase records for display.

## Gmail Sync

Gmail sync is intentionally split into discovery and hydration.

### Discovery

1. A user authorizes Gmail on the Gmail Creds page.
2. Tokens are stored in Supabase table `gm_tokens`.
3. Gmail Fetch runs `utils.gmail_backfill_ids.backfill_index_for_date_range(...)`.
4. The app stores lightweight rows in `gmail_message_index`:
   - `id`
   - `thread_id`
   - `ymd`
   - synthetic `internal_ms` anchored to the date bucket when exact metadata has not been fetched

Discovery avoids per-message metadata calls so it can scan large date ranges more quickly.

### Hydration

1. Gmail Fetch runs `utils.gmail_get_contents.fetch_and_store_messages_for_day(...)`.
2. Full message data is fetched from Gmail.
3. The app writes exact metadata and content into `gmail_messages`:
   - `id`
   - `thread_id`
   - `internal_ms`
   - `headers`
   - `snippet`
   - `body_full`
   - `raw_json`

## Gmail Search

1. `src/show_search_page.py` loads Gmail credentials.
2. The user submits a Gmail query.
3. Gmail API returns message IDs and message bodies.
4. Results are displayed in Streamlit.
5. An LLM summary can be generated from the fetched message content.

## Zoom Session Processing

1. `cron_app.py` runs the `Sessions` job.
2. AWS RDS Data API queries source session records.
3. Transcript references are resolved from S3.
4. `utils.utils_aws.save_to_supabase(...)` stores normalized rows in Supabase `zoom_sessions`.
5. Session pages display stored records and transcripts.

## QnA Processing

1. `cron_app.py` runs the `QnA` job.
2. It selects `zoom_sessions` rows with the initial QnA status for each date.
3. Prompts are loaded from `question_prompts`.
4. Each transcript is sent to the configured LLM.
5. Responses are stored in `session_qna`.
6. Session status is updated.
7. Grouped response emails are sent through AgentMail using recipients from `qna_emails`, falling back to `AGENTMAIL_TO_ADDRESS`.

## Finance Data

1. `cron_app.py` runs `BrainTree`.
2. Braintree transactions for the configured duration are synced into Supabase.
3. Finance pages read Braintree rows and generate summaries.
4. `FinanceMails` uses AgentMail to process configured finance mailbox messages.

## Token Count Processing

1. `cron_app.py` runs `TokenCount`.
2. Rows with negative or missing transcript token counts are selected by date.
3. Transcripts are normalized to text.
4. `tiktoken` counts tokens using `TOKEN_COUNT_ENCODING` or `cl100k_base`.
5. Supabase `zoom_sessions` rows are updated with token counts.

## Data Stores

- **Supabase**: Primary application database and OAuth token store.
- **Google Sheets**: Source for program roster and relationship data.
- **Gmail**: Source for communication search and stored message sync.
- **Google Calendar**: Source for calendar event context.
- **AWS RDS and S3**: Source systems for Zoom session records and transcript objects.
- **Braintree**: Payment and transaction source.
- **AgentMail**: Email sending and finance-mail processing.
