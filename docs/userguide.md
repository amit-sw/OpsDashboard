# User Guide

OpsDashboard is organized around the navigation tabs shown after Google login. The tabs you see depend on your assigned role.

## Sign In

1. Open the dashboard.
2. Select "Log in with Google".
3. Use your work Google account.
4. If you see Guest Access, ask an administrator to add your email to the authorized users table.

## Sidebar

The sidebar shows your name, email, verification status, profile image, and a logout button.

## User Students

Use "User's students" to see students related to your logged-in email. Student details are derived from the configured Google Sheets and Supabase records.

## Students

The Students page shows broader student data. Depending on your role, this can include student emails, parent emails, instructor, mentor, and operations ownership fields.

## Calendar

The Calendar page loads Google Calendar data and matches it with student records. Use it to inspect upcoming or recent student-related events.

## Email Search

The Email Search page searches Gmail using the authorized Gmail account.

Typical workflow:

1. Confirm Gmail access has been authorized.
2. Enter or adjust the Gmail search query.
3. Run Search.
4. Review matching messages.
5. Open the summary section when an LLM summary is needed.

## Past Sessions

Use Sessions to browse stored Zoom sessions. Session Details shows transcript and session-level detail. Some pages can generate answers or summaries using the configured LLM.

## Table Explorer

The Table Explorer shows rows from known Supabase tables. It is intended for operational inspection, not bulk editing.

## Sheet Explorer

The Sheet Explorer lets you browse Google Sheets available to the configured service account.

## Question Prompts

Question Prompts shows the prompt templates used for session QnA processing.

Depending on role:

- All authenticated non-guest users can review prompts and add new ones.
- Finance Admins and Super Admins can edit existing prompts.

## Gmail Fetch

Gmail Fetch syncs Gmail data into Supabase for a selected date range.

1. Choose start and end dates.
2. Review current coverage.
3. Select whether to include Spam and Trash.
4. Choose whether to fetch full message bodies.
5. Select "Sync Gmail to database".

The page shows discovery and fetch progress. You can also select "Show stored database messages" to inspect what is already in Supabase without calling Gmail.

## Finance Pages

Finance Admins can use Finance Agent and Braintree pages to inspect transaction data and generate finance-oriented summaries.

## QnA Emails

Finance Admins and Super Admins can manage recipient addresses for QnA prompt groups. These addresses are used by the background QnA email process.

## Recent Sessions

Super Admins can use New Sessions (24h) to review sessions created in the last 24 hours.
