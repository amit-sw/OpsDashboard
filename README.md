# OpsDashboard

Initial project scaffold for the OpsDashboard application. The repository currently provides:

- `app.py` as the runnable entry point.
- `src/` for core application modules (to be implemented).
- `test/` for automated tests.
- `doc/` for user-facing documentation.

Some key files:
- `utils/calendar_integration.py` exposes `CalendarClient` for Google Calendar access.
- `utils/supabase_integration.py' exposes 'SupabaseClient' for database access.
- `utils/posthog_integration.py` will centralize PostHog analytics helpers.

Update this document as features and dependencies are added.

For DB managers:
1. Remember to add specific schema to Project->Settings->API to "Exposed Schemas" list
2. For all schema changes, please update helpders/create_schema.sql

Entry points:
* app.py: Main entry point
* test_app.py: Used for testing sub-functionality in isolation during development
* helpers/ : Code written for non-App use (e.g. loading specific tables)

For deveelopers:
1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. streamlit run app.py
