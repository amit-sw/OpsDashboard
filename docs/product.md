# Product Overview

OpsDashboard is an internal operations dashboard for AI Club program staff. It brings together student records, Gmail communication, Google Calendar events, Zoom session transcripts, QnA summaries, and finance data in one Streamlit application.

The product is role-gated through Google login and Supabase-backed authorization. Users see navigation based on their assigned role in `authorized_users`.

## Goals

- Give staff a single place to inspect student, session, calendar, and email context.
- Support operations and finance workflows without giving every user direct database access.
- Make recurring operational jobs visible and testable from code.
- Store generated QnA and finance artifacts in Supabase for review and follow-up.

## Primary Users

- **User**: Can view assigned students, student details, calendar context, email search, past sessions, and read-only data exploration.
- **Admin**: Adds broader operational access, including Gmail fetch controls and cron exploration.
- **Finance Admin**: Adds finance agent, Braintree views, QnA email management, and finance-specific workflows.
- **Super Admin**: Adds Gmail credential management, broad data tools, QnA email management, and recent session monitoring.
- **Guest**: Authenticated but not authorized. Guests see an access request message only.

## Main Capabilities

- Google OAuth login through Streamlit.
- Role-based navigation.
- Student and relationship data sourced from Google Sheets and Supabase.
- Gmail credential storage, Gmail search, and date-range Gmail sync into Supabase.
- Google Calendar lookup and student matching.
- Zoom session browsing, transcript review, and LLM-assisted question answering.
- QnA prompt and recipient management.
- Braintree transaction syncing and finance summaries.
- Supabase table exploration for known application tables.
- Google Sheet exploration for configured service-account sheets.
- Background processing for sessions, QnA, Braintree, finance mail, and token counts.

## Non-Goals

- OpsDashboard is not a public customer-facing portal.
- It is not a replacement for Supabase Studio, Gmail, Google Calendar, or Braintree admin tools.
- It does not currently implement fine-grained per-row authorization inside each UI page; access is primarily role and page based.
