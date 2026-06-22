"""Agent Cost Control Room — wiring the budget monitor into the Antigravity SDK.

This is the live layer. A pre-tool Decide hook reads the SDK-native cumulative
token usage off the conversation (`agent.conversation.total_usage`) before each
tool call, accumulates it through the pure `update()` logic, surfaces the
per-checkpoint and cumulative cost, and — once the budget is exhausted — denies
every further tool call. That deny-all is the automated kill-switch: the SDK has
no `stop()` API, so denying tool calls is how you halt a runaway loop before it
degrades into token burn.

The pure budget logic lives in budget.py and is unit-tested offline; this file is
what you run to drive a real agent.

Run:
    python -m pip install google-antigravity
    python -m monitor.agent

Auth: set GOOGLE_CLOUD_PROJECT to use the Vertex AI backend (cloud-project /
enterprise auth via Application Default Credentials — run
`gcloud auth application-default login` first); otherwise set GEMINI_API_KEY.
"""

import asyncio
import os
from pathlib import Path

from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.hooks import PreToolCallDecideHook
from google.antigravity.types import HookResult

from .budget import decide, update

# Pin the agent's file root to this workspace.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The cost ceiling for this run. Tuned low so the kill-switch trips during a
# short, cheap demo; raise it for real work.
BUDGET = {
    "max_tokens": 40000,
    "warn_at_tokens": 25000,
    "usd_per_1k_tokens": 0.005,
}

DEFAULT_PROMPT = (
    "Analyze this project thoroughly: list the files, read the dashboard sources "
    "and the budget monitor, then write a detailed report of how the Cost Control "
    "Room computes spend."
)


def _auth_kwargs() -> dict:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        return {
            "vertex": True,
            "project": project,
            "location": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        }
    return {}


class CostKillSwitch(PreToolCallDecideHook):
    """Read live cumulative token usage; warn, then deny-all when over budget.

    `read_total` returns the conversation's cumulative `total_token_count`; it is
    wired to the live agent after construction. Each tool call we feed the *delta*
    since the last checkpoint into the pure `update()` logic, surface the monitor
    line, and let `decide()` halt the run once the budget is tripped.
    """

    def __init__(self, budget: dict):
        self.state = {"budget": budget, "usage": {"total_tokens": 0, "turns": 0}}
        self._last_total = 0
        self.read_total = lambda: 0  # set after the agent exists

    async def run(self, context, data) -> HookResult:
        live_total = int(self.read_total() or 0)
        delta = max(0, live_total - self._last_total)
        self._last_total = live_total

        result = update(delta, self.state)
        usage = {
            "total_tokens": result["cumulative_tokens"],
            "turns": result["turns"],
        }
        if result["state"] == "tripped":
            usage["state"] = "tripped"
            usage["stop_reason"] = result["stop_reason"]
        self.state["usage"] = usage

        if result["system_message"]:
            print(result["system_message"], flush=True)
        else:
            print(f"[cost] {result['cumulative_tokens']:,} tokens "
                  f"(budget {self.state['budget']['max_tokens']:,})", flush=True)

        verdict = decide(self.state["usage"])
        if verdict["decision"] == "deny":
            return HookResult(allow=False, message=verdict["reason"])
        return HookResult(allow=True)


async def main() -> None:
    import sys
    prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT

    kill_switch = CostKillSwitch(BUDGET)
    config = LocalAgentConfig(
        system_instructions=(
            "You are a release engineer. Work the task with the available tools. "
            "If a tool call is denied because the cost budget is exhausted, stop."
        ),
        workspaces=[str(PROJECT_ROOT)],
        hooks=[kill_switch],
        **_auth_kwargs(),
    )
    async with Agent(config) as agent:
        # Wire the kill-switch to the live cumulative usage.
        kill_switch.read_total = lambda: (
            agent.conversation.total_usage.total_token_count or 0
        )
        response = await agent.chat(prompt)
        print(await response.text())

        usage = agent.conversation.total_usage
        print("\n  --- Run cost ---")
        print(f"  Turns:           {agent.conversation.turn_count}")
        print(f"  Prompt tokens:   {usage.prompt_token_count:,}")
        print(f"  Output tokens:   {usage.candidates_token_count:,}")
        print(f"  Thinking tokens: {usage.thoughts_token_count:,}")
        print(f"  Total tokens:    {usage.total_token_count:,}")


if __name__ == "__main__":
    asyncio.run(main())
