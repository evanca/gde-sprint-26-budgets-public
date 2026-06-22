# Rule: Runaway-loop ceiling (kill-switch)

A rogue agent can loop on the same failing step — re-running tests, re-patching the
same assertion — without ever finishing. Token spend is one signal; turn count is
another, independent one.

- turn count **> `max_turns`** → **trip the kill-switch**: `update()` returns
  `state: "tripped"`, `action: "kill"`, with a `stop_reason` naming the turn count
  and the ceiling. As with the token cap, the kill-switch is then enforced by the
  deny-all Decide hook (the SDK has no stop() API).

This catches a loop that burns many cheap turns even before the token cap is hit.
It is checked **before** the token rules so an obvious loop is stopped first.

Ceiling for this build: `max_turns` (16 turns).
