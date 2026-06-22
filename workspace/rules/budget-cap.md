# Rule: Hard token budget (kill-switch)

Every model turn reports usage via `response.usage_metadata` (prompt, candidate,
cached, and thinking tokens). The monitor adds `total_token_count` to the running
total and compares against `data/budget.json`.

- projected total **≥ `max_tokens`** → **trip the kill-switch**: `update()`
  returns `state: "tripped"`, `action: "kill"`, with a `stop_reason`.
- the `stop_reason` states the projected tokens, the cap, and the dollar cost.

The Antigravity SDK has no dedicated stop()/continue=false API, so the kill-switch
is enforced as **deny-all**: once tripped, `decide(state)` returns a `deny`
decision, and the pre-tool Decide hook in `monitor/agent.py` denies every further
tool call — halting progress.
<!-- VERIFY: confirm whether the SDK exposes a turn/run stop control; if not,
     deny-all is the documented kill-switch. -->

Cap for this build: `max_tokens` (200,000 tokens). Fixture: `fixtures/turn-over.json`.
