# Repository Guidelines

## Project Structure & Module Organization
The entry point lives in `app.py`, while shared Python modules reside in `src/` (keep core helpers inside `src/core_utils.py`) and Streamlit helpers within `utils/`. Automated tests belong in `test/` with `test_app.py` mirroring `app.py` at the root, and user-facing docs are stored under `doc/`. Reuse any available patterns from `sample_code/` when introducing new modules, and reflect new capabilities in `README.md` plus `requirements.txt`.

## Build, Test, and Development Commands
Create an isolated environment with `python -m venv .venv` followed by `source .venv/bin/activate`, then `pip install -r requirements.txt`. Launch the dashboard via `streamlit run app.py` or the YouTube transcript helper through `streamlit run app_yt_private_download.py`. Run `pytest` from the repo root for the full suite; wire single-click runners (e.g., VS Code task or Make target) back to that command.

## Coding Style & Naming Conventions
Use 4-space indentation, Black-compatible spacing, and snake_case for files, modules, and functions; reserve PascalCase for classes and SCREAMING_SNAKE_CASE for constants. Keep every method under 30 lines and each file under 300 lines, preferring early returns over deep nesting. Small helper comments are welcome when logic is non-obvious, but favor expressive function names. Align new APIs with existing signatures in `src/core_utils.py` to avoid duplicated business rules.

## Testing Guidelines
Author tests in `test/` using `pytest`, naming files `test_<feature>.py` and functions `test_<behavior>()`. Cover both Streamlit utility boundaries (mock I/O) and integrations (e.g., Supabase, Google APIs) via fixtures or fakes so `pytest` runs quickly. Keep coverage close to feature parity: every new module or branch should ship with focused tests plus regression checks in `test_app.py` when app-level flows change.

## Commit & Pull Request Guidelines
Recent history uses short, descriptive summaries ("Added ability to process one session"), so continue writing imperative-style lines under ~65 characters and include scope when relevant. Each PR should describe the change, list test evidence (`pytest`, Streamlit smoke run), link issues, and add before/after screenshots for UI changes. Highlight schema or config updates in the PR body and coordinate doc updates in `doc/` when user workflows shift.

## Security & Configuration Tips
Never commit `.env`, `.venv`, `.streamlit/secrets.toml`, or JSON credential files; use Streamlit Secrets or local `.env` loading instead. Preserve the union of `.gitignore` entries already in the repo (e.g., `.DS_Store`, `*.pyo`, `*.pkl`) when adding the required `.env`, `.venv`, `.streamlit/secrets.toml`, and `*.json` patterns so future refreshes don’t drop ignores. Store Supabase and Google keys locally and document any required environment variables inside `README.md` plus `doc/`. Remove tokens after testing (`.tokens/`) and rotate credentials when switching between Gmail and YouTube OAuth apps.

Whenever you add a new table or sequence inside the `opsdashboard` schema, also create a matching `public.<table>` view that selects from the base table and `GRANT SELECT, INSERT, UPDATE, DELETE` on that view to both the `authenticated` and `anon` roles. This keeps the Supabase API surface consistent without exposing the base schema directly.
