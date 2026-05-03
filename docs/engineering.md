# Engineering Guide

OpsDashboard is a Python Streamlit app with supporting utilities and cron-style processing code.

## Project Layout

- `app.py`: Main Streamlit entry point.
- `src/verified_ui.py`: Login-aware role routing and navigation.
- `src/show_*.py`: Streamlit page modules.
- `utils/`: Integration clients and shared service helpers.
- `cron_app.py`: Batch processing entry point for operational jobs.
- `helpers/`: One-off load scripts, SQL helpers, and support utilities.
- `scripts/`: Reusable operational scripts such as prompt seeding.
- `test/`: Pytest suite for app utilities, integrations, and page behavior.
- `docs/`: Project documentation.

## Runtime Model

`app.py` loads Streamlit secrets into `utils.configs`, copies configured `[env]` values into environment variables, and routes users through Google login. Logged-in users are looked up in Supabase table `authorized_users`; the role controls which page groups are shown.

The UI uses Streamlit's `st.navigation` with page functions imported from `src/show_*.py`. Page modules instantiate integration clients as needed, usually from environment variables and `st.secrets`.

## Key Modules

- `utils/supabase_integration.py`: Central Supabase wrapper. It exposes known tables, Gmail index/message operations, Zoom session operations, QnA prompts, QnA email recipients, YouTube records, and Braintree helpers.
- `utils/gmail_creds.py`: Gmail OAuth configuration and token storage.
- `utils/gmail_backfill_ids.py`: Gmail discovery/indexing for date ranges.
- `utils/gmail_get_contents.py`: Gmail hydration/fetch of message contents.
- `utils/process_gsheets.py`: Google Sheets loading and user-to-student relationship helpers.
- `utils/calendar_integration.py`: Google Calendar API access.
- `utils/utils_aws.py`: AWS RDS Data API and S3 transcript helpers.
- `utils/utils_transcript_chat.py`: LLM calls for transcript QnA.
- `utils/prompts.py`: Prompt loading from Supabase with local defaults.
- `utils/braintree_integration.py`: Braintree transaction sync.
- `utils/agentmail_integration.py`: Finance mailbox processing through AgentMail.
- `src/langsmith_logging.py`: Optional LangSmith tracing helpers.

## Role Routing

`src/verified_ui.py` defines these role handlers:

- `show_ui_user`
- `show_ui_admin`
- `show_ui_financeadmin`
- `show_ui_superadmin`
- `show_ui_guest`

When adding a page, import the page function in `src/verified_ui.py`, add it to the intended role's navigation map, and add tests for any non-trivial page logic.

## Coding Guidelines

- Keep page modules focused on UI orchestration.
- Put reusable business logic in `utils/` or `src/core_utils.py`.
- Keep Supabase access behind `SupabaseClient` when possible.
- Prefer small functions with early returns over deeply nested Streamlit blocks.
- Keep external API calls mockable in tests.
- Do not commit secrets, tokens, or local virtual environments.

## Testing

Run the full suite with:

```bash
pytest
```

Focused tests should live in `test/test_<feature>.py`. Mock external services such as Supabase, Gmail, Google APIs, AWS, AgentMail, Braintree, and OpenAI so local tests remain fast and deterministic.

## Adding Tables

Application base tables are normally created in the `opsdashboard` schema and exposed through public views for Supabase/PostgREST access. When adding a new table or sequence in `opsdashboard`, also create a matching `public.<table>` view and grant `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on that view to `authenticated` and `anon` unless the feature explicitly requires a narrower policy.
