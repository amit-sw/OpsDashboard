# Troubleshooting

## Pull or Push Uses the Wrong GitHub Account

If GitHub offers to create a fork or says you do not have permission, the remote or credential identity is wrong.

Check:

```bash
git remote -v
ssh -T git@github-amitsw
```

For the AmitSW workspace, the remote should use the AmitSW SSH alias:

```bash
git remote set-url origin git@github-amitsw:amit-sw/OpsDashboard.git
```

The SSH test should greet the `amit-sw` account.

## Login Works but User Sees Guest Access

The email is authenticated but not authorized.

Check Supabase table `authorized_users` for the exact Google account email. Add or update the row with the correct role.

## Supabase Credentials Are Missing

Pages that use Supabase require `SUPABASE_URL` and `SUPABASE_KEY`. In Streamlit, put them under `[env]` in secrets so `app.py` can copy them into environment variables.

## Supabase Table Explorer Does Not Show a Table

`SupabaseClient.list_known_tables()` only exposes the hard-coded known table list in `utils/supabase_integration.py`. Add the table there if it is intentionally part of the app surface.

Also confirm that the database object is exposed through a public view or configured schema and has grants for the API roles.

## Gmail Fetch Says Credentials Are Invalid

Open the Gmail Creds page and authorize Gmail again. The Gmail Fetch and Search pages expect a valid token from `gm_tokens`.

If Gmail scopes changed, reauthorize rather than reusing old tokens.

## Gmail Sync Is Slow

The sync has two stages:

1. Discovery stores lightweight message IDs.
2. Hydration fetches message contents.

Large date ranges can still take time, especially during hydration. Start with a small range, verify coverage, then expand.

## Gmail Coverage Shows Indexed IDs but Missing Messages

This means discovery completed but hydration did not fetch all message bodies. Run "Sync Gmail to database" again for the same date range. The process is designed to skip already-complete rows and fill missing content.

## Calendar or Sheet Pages Are Empty

Check:

- The Google service account has access to the configured Sheets.
- `st.secrets["gdrive_secrets"]` contains the configured sheet list.
- Source sheets include the expected columns, especially `Email`.
- Calendar settings exist under `st.secrets["calendar"]`.

## QnA Job Does Not Send Email

Check:

- `AGENTMAIL_API_KEY`
- `AGENTMAIL_FROM_ADDRESS`
- `AGENTMAIL_TO_ADDRESS` fallback
- Rows in `qna_emails` for the prompt groups being processed
- Active prompts in `question_prompts`
- `OPENAI_API_KEY`

The QnA job updates session status after processing; review `zoom_sessions` and `session_qna` to see how far it got.

## Sessions Job Fails to Fetch Zoom Data

Check:

- `AWS_REGION`
- `AWS_CLUSTER_ARN`
- `AWS_SECRET_ARN`
- `AWS_DB_NAME`
- AWS permissions for RDS Data API
- S3 permissions for transcript objects

The CRON explorer page may use older variable names: `REGION`, `CLUSTER_ARN`, `SECRET_ARN`, and `DB_NAME`.

## Token Counts Stay Negative

Run the `TokenCount` job and verify transcripts are present. Empty transcripts are skipped. If the encoding name is invalid, the code falls back to `cl100k_base`.

## Braintree Pages or Sync Fail

Check:

- `BRAINTREE_MERCHANT_ID`
- `BRAINTREE_PUBLIC_KEY`
- `BRAINTREE_PRIVATE_KEY`
- Supabase writes to `braintree_transactions`

## Tests Fail Due to Missing Optional SDKs

Install dependencies from `requirements.txt`. Many modules defensively handle missing SDKs in unit tests, but integration-heavy tests still assume project dependencies are installed.
