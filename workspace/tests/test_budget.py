"""Offline tests for the token-budget monitor.

Run from the project root with:  python -m unittest
No agent, no network, no SDK install required — `update()`/`decide()` are pure
logic. These are the JS monitor tests (the old tests/cost.test.js `decide`/
`tokensOf` suite) ported to Python, since the monitor now runs on the Antigravity
SDK (Python). The web/dashboard pure-function tests stay in JS
(tests/console.test.js).
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from monitor.budget import update, decide, tokens_of  # noqa: E402

FIXTURES = ROOT / "fixtures"

BUDGET = {
    "max_tokens": 200000,
    "warn_at_tokens": 150000,
    "max_turns": 16,
    "usd_per_1k_tokens": 0.005,
}


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def turn(name, total_tokens=0, turns=0):
    """update() for one fixture turn against a prior cumulative state."""
    state = {"budget": BUDGET, "usage": {"total_tokens": total_tokens, "turns": turns}}
    return update(tokens_of(fixture(name)), state)


class BudgetMonitor(unittest.TestCase):
    # --- Monitor decision contract ---

    def test_a_turn_under_budget_is_allowed_silently(self):
        result = turn("turn-normal", total_tokens=0, turns=0)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["action"], "allow")
        self.assertIsNone(result["system_message"])

    def test_crossing_the_warn_line_surfaces_a_message_but_does_not_kill(self):
        result = turn("turn-warn", total_tokens=100000, turns=5)
        self.assertEqual(result["state"], "warn")
        self.assertNotEqual(result["action"], "kill")
        self.assertIn("% of", result["system_message"])

    def test_exhausting_the_token_budget_trips_the_kill_switch(self):
        result = turn("turn-over", total_tokens=181000, turns=11)
        self.assertEqual(result["action"], "kill")
        self.assertEqual(result["state"], "tripped")
        self.assertIn("budget exhausted", result["stop_reason"])

    def test_a_runaway_loop_trips_the_kill_switch_on_turn_count(self):
        result = turn("turn-normal", total_tokens=1000, turns=16)
        self.assertEqual(result["action"], "kill")
        self.assertIn("runaway loop", result["stop_reason"])

    def test_the_runaway_ceiling_is_checked_before_the_token_cap(self):
        result = turn("turn-over", total_tokens=199000, turns=16)
        self.assertEqual(result["action"], "kill")
        self.assertIn("runaway loop", result["stop_reason"])

    def test_every_kill_decision_carries_a_stop_reason(self):
        result = turn("turn-over", total_tokens=181000, turns=11)
        self.assertIsInstance(result["stop_reason"], str)
        self.assertGreater(len(result["stop_reason"]), 0)

    # --- Deny-all kill-switch (the SDK has no stop() API) ---

    def test_decide_denies_all_tool_calls_once_tripped(self):
        result = turn("turn-over", total_tokens=181000, turns=11)
        verdict = decide(result)
        self.assertEqual(verdict["decision"], "deny")
        self.assertIn("budget exhausted", verdict["reason"])

    def test_decide_allows_tool_calls_while_under_budget(self):
        result = turn("turn-normal", total_tokens=0, turns=0)
        self.assertEqual(decide(result)["decision"], "allow")

    # --- Token accounting ---

    def test_tokens_of_reads_the_sdk_token_count(self):
        self.assertEqual(tokens_of(fixture("turn-normal")), 8000)

    def test_non_model_events_count_as_zero_tokens(self):
        self.assertEqual(tokens_of(fixture("not-a-model-event")), 0)


if __name__ == "__main__":
    unittest.main()
