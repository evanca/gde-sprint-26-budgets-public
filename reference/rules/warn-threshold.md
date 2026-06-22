# Rule: Warn threshold (accumulation monitor)

Before the cap, the agent should *see* it coming.

- projected total **≥ `warn_at_tokens`** but **< `max_tokens`** → **allow**, but
  `update()` returns `state: "warn"`, `action: "warn"`, and a `system_message`
  reporting the cumulative tokens and the percentage of budget used.
- below `warn_at_tokens` → **allow silently** (`state: "ok"`): no noise on cheap
  turns.

The warn line surfaces the live token accumulation so the human (or the agent) can
choose a bounded recovery — summarize context, switch to a cheaper model, or stop.

Warn line for this build: `warn_at_tokens` (150,000). Fixture: `fixtures/turn-warn.json`.
