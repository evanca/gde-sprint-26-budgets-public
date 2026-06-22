# Rule: Cost accounting & the ledger

The Cost Control Room renders `data/usage.json` — one entry per model turn with
`tokens`, `toolCalls`, `retries`, and `compactions`. The dashboard rolls these up:

- **cumulative tokens** and **cumulative cost** (`tokens / 1000 × usdPer1kTokens`).
- **budget level** per turn: `ok` → `warn` → `over` (see `js/board.js#assess`).
- totals for tool calls, retries, and context compactions.

Context-compaction events are a cost signal — frequent compactions mean the agent
keeps re-loading context, worth seeing next to tokens (`js/board.js#note`).

The monitor (`monitor/budget.py`) and the board share the same budget file
(`data/budget.json`) so the live kill-switch and the dashboard always agree.
