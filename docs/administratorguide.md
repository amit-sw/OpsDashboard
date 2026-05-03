# Administrator Guide

This guide covers operational tasks for Super Admins, Finance Admins, and maintainers.

## Managing Access

User access is controlled by Supabase table `authorized_users`.

Required fields:

- `email`: Exact Google account email.
- `role`: One of `guest`, `user`, `admin`, `financeadmin`, or `superadmin`.

If a user can log in but sees Guest Access, add or update their row.

## First Admin Setup

1. Deploy the app with Supabase credentials configured.
2. Apply schema SQL from `helpers/create_schema.sql` and `helpers/create_schema_gmail.sql`.
3. Add a `superadmin` row for the first administrator in `authorized_users`.
4. Confirm the administrator can log in and see SuperAdmin pages.

## Gmail Administration

Use the Gmail Creds page to authorize Gmail access. The token is stored in Supabase table `gm_tokens`.

Use Gmail Fetch to sync message data into:

- `gmail_message_index`
- `gmail_messages`

For large backfills, use smaller date ranges first and confirm coverage before expanding.

## QnA Prompt Administration

Use Question Prompts to manage QnA prompt rows.

Important fields:

- `title`: Display name and question topic.
- `prompt`: Instruction sent to the LLM.
- `prompt_group`: Group used for email routing.
- `status`: Active prompts are used by the QnA process.

Seed default prompts with:

```bash
python scripts/seed_question_prompts.py
```

## QnA Email Administration

Use QnA Emails to map prompt groups to recipient emails. The QnA background job sends one email per prompt group. If no group-specific recipient exists, the job falls back to `AGENTMAIL_TO_ADDRESS`.

## Supabase Administration

Keep base application data in the `opsdashboard` schema. Expose API-facing data through public views where needed.

When adding a table or sequence:

1. Create the base table in `opsdashboard`.
2. Create a matching `public.<table>` view.
3. Set `security_invoker = true` when RLS should apply through the view.
4. Grant `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on the view to `authenticated` and `anon`, unless the feature requires narrower privileges.
5. Add the table to `USED_SUPABASE_TABLES` in `utils/supabase_integration.py` if the Table Explorer should expose it.
6. Add focused tests for the client method or page using the table.

## Running Cron Processing

Run all configured jobs with:

```bash
python cron_app.py
```

The runner executes:

- `Sessions`: Imports Zoom session records and transcript content from AWS.
- `QnA`: Runs active prompts against initial Zoom sessions and sends QnA emails.
- `BrainTree`: Syncs Braintree transactions.
- `FinanceMails`: Processes finance mailbox messages.
- `TokenCount`: Recomputes missing or negative transcript token counts.

Set `duration` to control how many days the jobs scan.

## Secret Rotation

Rotate secrets when access changes or after testing with temporary credentials.

Common secrets:

- Supabase API keys
- Google OAuth credentials
- Google service-account credentials
- Gmail OAuth tokens in `gm_tokens`
- AWS credentials and ARNs
- Braintree keys
- AgentMail API key
- OpenAI API key
- LangSmith key

Remove local `.tokens/` files after testing.

## Operational Checks

Before a release:

- Run `pytest`.
- Confirm Streamlit starts with `streamlit run app.py`.
- Confirm the intended admin account can log in.
- Verify Supabase credentials and exposed views.
- Smoke-test Gmail credentials if Gmail pages changed.
- Smoke-test QnA on a small date range if prompt, LLM, or email code changed.
- Check that no secret files are staged.
