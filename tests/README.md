Run `.venv/bin/python -m pip install -r requirements-dev.txt`, then
`.venv/bin/python -m pytest -q` from the repository root.

Tests use synthetic bars and temporary SQLite databases. No API keys or market
connections are needed. The database fixture redirects config before importing
database-dependent modules; do not import db or journal at test-module scope.

Known semantics and discrepancies (no production fixes included):
- Backtests permit overlapping signals after ten bars; journals block another
  trade in the same symbol/variant while the previous trade remains open.
- Journal replay recomputes sizing from current configuration rather than a
  historical configuration snapshot.
- Drawdown is calculated from ordered trade returns, not daily marked equity.
- Open simulation states include estimated round-trip costs, whereas newly
  inserted journal rows initially store zero R.
