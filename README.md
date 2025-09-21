# OpsDashboard

Initial project scaffold for the OpsDashboard application. The repository currently provides:

- `app.py` as the runnable entry point.
- `src/` for core application modules (to be implemented).
- `test/` for automated tests.
- `doc/` for user-facing documentation.

Some key files:
- `utils/calendar_integration.py` exposes `CalendarClient` for Google Calendar access.
- `helpers/test_creds2.py` provides a prototype Gmail read-only OAuth + search utility.

Update this document as features and dependencies are added.

For DB managers:
1. Remember to add specific schema to Project->Settings->API to "Exposed Schemas" list

For deveelopers:
1. python -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. streamlit run app.py
