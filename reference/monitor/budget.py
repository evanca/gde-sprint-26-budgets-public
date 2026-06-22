"""Agent Cost Control Room — the token-budget monitor (pure logic).

This module is intentionally free of any SDK import so the budget logic can be
unit-tested offline (see ../tests/test_budget.py) without spawning an agent.
`agent.py` wires `update()`/`decide()` into the Antigravity SDK: it reads each
turn's `response.usage_metadata` and feeds the token count in here.

Contract for update(turn_tokens, state):
  turn_tokens : int   — this turn's tokens (see tokens_of() for the SDK shape)
  state       : dict { "budget": {...}, "usage": {"total_tokens", "turns"} }
  returns     : dict
    {
      "turn_tokens": int,
      "cumulative_tokens": int,
      "turns": int,
      "state": "ok" | "warn" | "tripped",
      "action": "allow" | "warn" | "kill",
      "system_message": str | None,   # surfaced when state != "ok"
      "stop_reason": str | None,       # set when action == "kill"
    }

KILL-SWITCH MODEL: the Antigravity SDK has no dedicated stop()/continue=false
API. Once the accumulated budget is exceeded (state "tripped"), `decide()` denies
all further tool calls — the deny-all decision is the documented kill-switch.
agent.py turns `decide()` into a PreToolCallDecideHook returning allow=False.
"""


def tokens_of(response_like):
    """Pull the SDK-native token count out of a response/turn payload.

    The Antigravity SDK reports per-turn and cumulative usage via
    `response.usage_metadata` (prompt, candidate, cached, and thinking tokens):
    e.g. `response.usage_metadata.total_token_count` and
    `response.usage_metadata.thoughts_token_count`. Here we accept a plain dict
    (as the fixtures provide) so the logic stays SDK-free and offline-testable.

    Anything that is not a turn with usage contributes zero tokens.
    """
    if not isinstance(response_like, dict):
        return 0
    meta = response_like.get("usage_metadata")
    if not isinstance(meta, dict):
        return 0
    return int(meta.get("total_token_count") or 0)


def _fmt(n):
    return f"{int(n or 0):,}"


def _cost(tokens, rate=0):
    return ((int(tokens) or 0) / 1000) * (rate or 0)


def update(turn_tokens, state=None):
    """Accumulate one turn against the budget and classify the result."""
    state = state or {}
    budget = state.get("budget") or {}
    usage = state.get("usage") or {"total_tokens": 0, "turns": 0}

    turn_tokens = int(turn_tokens or 0)
    cumulative = int(usage.get("total_tokens") or 0) + turn_tokens
    turns = int(usage.get("turns") or 0) + 1

    result = {
        "turn_tokens": turn_tokens,
        "cumulative_tokens": cumulative,
        "turns": turns,
        "state": "ok",
        "action": "allow",
        "system_message": None,
        "stop_reason": None,
    }

    max_turns = budget.get("max_turns")
    max_tokens = budget.get("max_tokens")
    warn_at = budget.get("warn_at_tokens")
    rate = budget.get("usd_per_1k_tokens")

    # Kill-switch 1 — runaway loop: too many model turns for one task.
    # Checked first, so an obvious loop is stopped even on cheap turns.
    if max_turns and turns > max_turns:
        result["state"] = "tripped"
        result["action"] = "kill"
        result["stop_reason"] = (
            f"runaway loop — {turns} model turns exceeds the "
            f"{max_turns}-turn ceiling"
        )
        result["system_message"] = f"🛑 Cost kill-switch — {result['stop_reason']}"
        return result

    # Kill-switch 2 — cumulative token budget exhausted.
    if max_tokens and cumulative >= max_tokens:
        usd = f"{_cost(cumulative, rate):.2f}"
        result["state"] = "tripped"
        result["action"] = "kill"
        result["stop_reason"] = (
            f"budget exhausted — {_fmt(cumulative)} tokens ≥ the "
            f"{_fmt(max_tokens)} cap (~${usd})"
        )
        result["system_message"] = f"🛑 Cost kill-switch — {result['stop_reason']}"
        return result

    # Warn tier — approaching the cap; surface the accumulation monitor.
    if warn_at and cumulative >= warn_at:
        pct = round((cumulative / max_tokens) * 100) if max_tokens else 0
        result["state"] = "warn"
        result["action"] = "warn"
        result["system_message"] = (
            f"⚠️ Cost monitor: {_fmt(cumulative)} tokens — {pct}% of the "
            f"{_fmt(max_tokens)} budget"
        )
        return result

    return result  # under budget: allow silently


def decide(state=None):
    """The deny-all kill-switch decision for a pre-tool Decide hook.

    Once the budget is tripped, deny every further tool call — this is how the
    kill-switch is modeled on the Antigravity SDK, which exposes no stop() API.
    """
    state = state or {}
    if state.get("state") == "tripped":
        reason = state.get("stop_reason") or "budget exhausted"
        return {"decision": "deny", "reason": reason,
                "system_message": f"🛑 Cost kill-switch — {reason}"}
    return {"decision": "allow"}
