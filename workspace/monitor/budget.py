"""Agent Cost Control Room — the token-budget monitor (pure logic).

⚠️ STARTER STUB: this currently ACCOUNTS FOR NOTHING. Every model turn is allowed,
no matter how many tokens it burns — there is no kill-switch. Your job in this
codelab is to implement the monitor described in ../rules/*.md.

This module is intentionally free of any SDK import so the budget logic can be
unit-tested offline (see ../tests/test_budget.py) without spawning an agent.
`agent.py` wires `update()`/`decide()` into the Antigravity SDK: it reads each
turn's `response.usage_metadata` and feeds the token count in here.

Contract for update(turn_tokens, state):
  turn_tokens : int   — this turn's tokens (see tokens_of() for the SDK shape)
  state       : dict { "budget": {...}, "usage": {"total_tokens", "turns"} }
  returns     : dict with keys turn_tokens, cumulative_tokens, turns, state
                ("ok"|"warn"|"tripped"), action ("allow"|"warn"|"kill"),
                system_message, stop_reason.

KILL-SWITCH MODEL: the Antigravity SDK has no dedicated stop()/continue=false
API. Once the accumulated budget is exceeded (state "tripped"), `decide()` must
deny all further tool calls — the deny-all decision is the documented kill-switch.

Implement the rules in ../rules/*.md until `python -m unittest` is green.
"""


def tokens_of(response_like):
    # TODO(codelab): return response.usage_metadata.total_token_count
    #   (0 for anything that is not a turn with usage).
    return 0


def update(turn_tokens, state=None):
    # TODO(codelab): accumulate turn_tokens against state["usage"], then classify
    #   against state["budget"] (runaway loop, cap, warn line, otherwise ok).
    return {
        "turn_tokens": 0,
        "cumulative_tokens": 0,
        "turns": 0,
        "state": "ok",
        "action": "allow",
        "system_message": None,
        "stop_reason": None,
    }


def decide(state=None):
    # TODO(codelab): deny all tool calls once state["state"] == "tripped";
    #   otherwise allow. This deny-all is the kill-switch (no SDK stop() API).
    return {"decision": "allow"}
