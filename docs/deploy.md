# Deployment Guide

OpsDashboard is deployed as a Streamlit application plus optional batch processing through `cron_app.py`.

## Prerequisites

- Python 3.11 or compatible runtime.
- Supabase project with required tables, views, grants, and exposed schemas.
- Google OAuth configuration for Streamlit login and Gmail access.
- Google service account access to configured Sheets.
- Optional integrations as needed:
  - AWS RDS Data API and S3 for Zoom session ingestion.
  - OpenAI API for transcript and email summaries.
  - Braintree API for finance sync.
  - AgentMail API for QnA email delivery and finance mailbox processing.
  - LangSmith API for tracing.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Run tests with:

```bash
pytest
```

## Streamlit Secrets

The app reads `st.secrets` at startup. The common structure is:

```toml
[auth]
redirect_uri = "https://aiclubops.streamlit.app/~/+/oauth2callback"
cookie_secret = "generate-a-long-random-secret-and-keep-it-stable"
client_id = "..."
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[env]
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
SUPABASE_SERVICE_ROLE_KEY = "..."
OPENAI_API_KEY = "..."
OPENAI_MODEL = "gpt-5-mini"
AGENTMAIL_API_KEY = "..."
AGENTMAIL_FROM_ADDRESS = "..."
AGENTMAIL_TO_ADDRESS = "..."
BRAINTREE_MERCHANT_ID = "..."
BRAINTREE_PUBLIC_KEY = "..."
BRAINTREE_PRIVATE_KEY = "..."
AWS_REGION = "..."
AWS_CLUSTER_ARN = "..."
AWS_SECRET_ARN = "..."
AWS_DB_NAME = "..."
TOKEN_COUNT_ENCODING = "cl100k_base"

[gdrive_secrets]
# Google service-account fields and configured sheets.

[calendar]
# Google Calendar API configuration.

[gmail_oauth]
# Gmail OAuth client configuration.

[posthog]
# Optional analytics configuration.
```

For Streamlit Community Cloud, keep `auth.redirect_uri` exactly aligned with
the deployed callback URL, including the `~/+/oauth2callback` path segment, and
enter the same URL in the Google OAuth client's authorized redirect URIs. Keep
`auth.cookie_secret` stable across redeploys; changing it invalidates in-flight
login state and can surface as a callback `mismatching_state` error.

Some older page helpers use `REGION`, `CLUSTER_ARN`, `SECRET_ARN`, and `DB_NAME` for AWS fetches. Keep those aliases populated if the CRON explorer page is used.

## Supabase Setup

1. Apply `helpers/create_schema.sql`.
2. Apply `helpers/create_schema_gmail.sql`.
3. Ensure the Supabase API exposes the required schema or public views.
4. Seed default QnA prompts when needed:

```bash
python scripts/seed_question_prompts.py
```

5. Add users to `authorized_users` with one of the supported roles:
   - `guest`
   - `user`
   - `admin`
   - `financeadmin`
   - `superadmin`

## Running Batch Jobs

Run all cron jobs locally with:

```bash
python cron_app.py
```

The default duration is two days. Override it with the `duration` environment variable.

The batch runner processes:

- `Sessions`
- `QnA`
- `BrainTree`
- `FinanceMails`
- `TokenCount`

For hosted deployments, schedule `cron_app.py` in the platform scheduler or a separate worker environment with the same environment variables.

## Deployment Checklist

- Dependencies installed from `requirements.txt`.
- Secrets configured in Streamlit or the hosting environment.
- Supabase schema and public views applied.
- Supabase API settings include the required schema/views.
- Google login uses `https://aiclubops.streamlit.app/~/+/oauth2callback` in both Streamlit Secrets and the Google OAuth client.
- Gmail OAuth redirect URLs match the deployed URL configured for the Gmail helper.
- Service-account sheets are shared with the configured Google service account.
- AWS, Braintree, AgentMail, and OpenAI keys are present for enabled workflows.
- A `superadmin` user exists for first operational access.
- `pytest` passes before deployment.

## Files Not to Deploy or Commit

Do not commit:

- `.env`
- `.venv`
- `.streamlit/secrets.toml`
- `.tokens/`
- Google credential JSON files
- Pickle or generated local cache files
