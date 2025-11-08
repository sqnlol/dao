### Quick context

- Project: "CS2 Skin Analyzer" — a desktop Tkinter app (Python) that fetches Steam Market listings and price history, stores them in a local SQLite DB, and displays results in a small MVC-like GUI.
- Entry point: `src/main.py` (run from repo root as `python src/main.py`).

### Big picture for code changes

- Main controller: `src/gui/app.py` — `MarketApp` manages views, holds session state (notably `login_cookie`), runs background threads and polls `self.result_queue` (every 100ms) for messages from workers.
- Views live under `src/gui/` (`login_view.py`, `search_view.py`, `results_view.py`) — they are lightweight UI shells; business logic lives in `src/steam_market.py` and persistence in `src/database.py`.
- Networking: `src/steam_market.py` contains all Steam HTTP calls. It expects a browser-like User-Agent for listings and requires `steamLoginSecure` cookie for price history.
- Persistence: `src/database.py` uses `steam_market.db` (project root) and a `sales` table with UNIQUE(market_hash_name, sale_timestamp, price) to avoid duplicates.

### Important patterns & conventions (do NOT change without updating callers)

- Threading & messages: background threads must push dicts into the controller queue with keys: `status` in {'log','error','success'}. For `success`, include `item_name`, `history_data`, `listings_data` (examples in `SearchView._search_worker`). The controller expects these exact keys when switching to results view.
- Error handling style: network/db helpers print errors to stdout/stderr and generally return `None` on failure (rather than raising). Follow this pattern for consistent behavior with the UI.
- DB migration: schema lives in `database.init_db()`; adding/removing columns requires migrating data manually (no migration tool present). Keep `UNIQUE(market_hash_name, sale_timestamp, price)` when inserting sales.
- Currency / price conversion: `get_market_listings` returns prices by converting Steam integer-cent values to floats via `/100.0`. Listings use `converted_price` + `converted_fee` -> divide by 100.

### Key files & quick edit guide

- Add/change API parsing / logic: `src/steam_market.py`
  - Price history: `get_price_history(market_hash_name, login_cookie)` — requires `login_cookie` (`steamLoginSecure`) and returns a list of dicts with `sale_timestamp`, `sale_date_str`, `price`, `sales_count`.
  - Listings: `get_market_listings(market_hash_name, count)` — respects `country='PL'`, `language='polish'`, `currency=6` (PLN).
  - Full item list (autocompletion): `fetch_all_csgo_items()` writes to `src/suggestions.txt` and may be long-running; it's already run in a background thread by `MarketApp`.

- UI / flow changes: `src/gui/app.py` — change how results are handed to views here. Views assume `show_results(item_name, history_data, listings_data)` signature in `ResultsView`.

- DB changes: `src/database.py` — update `init_db()` and `add_sales()` together; `add_sales()` intentionally swallows `sqlite3.IntegrityError` for duplicates.

### Developer workflows / commands

- Install deps: `pip install -r requirements.txt` (file present in repo root). The code checks for `requests` in `src/main.py` and prints the same suggestion.
- Run the app (from repo root): `python src/main.py` (or `cd src; python main.py`).

### Integration pitfalls & gotchas discovered here

- Price history will fail silently (returns `None`) if `steamLoginSecure` cookie is missing or expired — tests and changes that depend on price history should either mock `steam_market.get_price_history` or provide a stable cookie.
- Many Steam endpoints will return different structures depending on language/country parameters and rate-limiting; preserve existing `User-Agent`, `currency=6` and `country='PL'` unless intentionally changing locale.
- `SUGGESTIONS_FILE` is `src/suggestions.txt` — `MarketApp` expects it there. `fetch_all_csgo_items()` writes into that path; keep path usage consistent.

### Examples for common tasks

- To add a new field to stored sales (e.g., `float_condition`):
  1. Update `init_db()` to add column and optionally write a one-off migration.
  2. Update `add_sales()` to include the new field in inserts.
  3. Update callers that build `sales_records` (e.g., `get_price_history`/search worker) to supply the field.

- To change how results are displayed in the GUI: modify `ResultsView.show_results(...)` and ensure `MarketApp.switch_view('results', ...)` still passes `history_data` and `listings_data`.

If any part of this summary is unclear or you'd like me to include additional examples (e.g., sample queue messages, JSON snippets from Steam responses, or a short unit-test template for `steam_market`), tell me which area to expand and I will iterate.
