// Pure, dependency-free helpers for the Agent Cost Control Room.

export const LEVELS = ["ok", "warn", "over"];

export const LEVEL_LABELS = {
  ok: "On budget",
  warn: "Approaching cap",
  over: "Over budget"
};

// Dollar cost of a token count at the configured rate.
export function costOf(tokens, usdPer1kTokens = 0) {
  return ((Number(tokens) || 0) / 1000) * usdPer1kTokens;
}

// Budget level + percentage for a cumulative token total.
export function assess(cumulativeTokens, budget = {}) {
  const max = budget.maxTokens || Infinity;
  const warn = budget.warnAtTokens || max;
  const pct = budget.maxTokens ? Math.round((cumulativeTokens / budget.maxTokens) * 100) : 0;
  let level = "ok";
  if (cumulativeTokens >= max) level = "over";
  else if (cumulativeTokens >= warn) level = "warn";
  return { level, pct };
}

// Annotate each turn with its running cumulative total, cost, and budget level.
export function accumulate(turns, budget = {}) {
  let running = 0;
  return turns.map((turn) => {
    running += Number(turn.tokens) || 0;
    return {
      ...turn,
      cumulativeTokens: running,
      cost: costOf(turn.tokens, budget.usdPer1kTokens),
      cumulativeCost: costOf(running, budget.usdPer1kTokens),
      ...assess(running, budget)
    };
  });
}

// Roll the per-turn ledger up into the headline numbers for the control room.
export function summarize(turns, budget = {}) {
  const rows = accumulate(turns, budget);
  const totalTokens = rows.length ? rows[rows.length - 1].cumulativeTokens : 0;
  const sum = (key) => turns.reduce((n, t) => n + (Number(t[key]) || 0), 0);
  return {
    turns: turns.length,
    totalTokens,
    totalCost: costOf(totalTokens, budget.usdPer1kTokens),
    toolCalls: sum("toolCalls"),
    retries: sum("retries"),
    compactions: sum("compactions"),
    ...assess(totalTokens, budget)
  };
}

// Index of the first turn whose cumulative spend crosses the hard cap (-1 if none).
export function firstBreach(turns, budget = {}) {
  return accumulate(turns, budget).findIndex((turn) => turn.level === "over");
}

// Context-compaction observability: frequent compactions are a cost signal —
// the agent keeps re-loading context. Surfaced on the Cost Control Room next to
// tokens, retries, and tool calls.
export function note(input = {}) {
  const trigger = input.trigger === "manual" ? "manual" : "automatic";
  return { systemMessage: `🗜️ Context compaction (${trigger}) — logged to the Cost Control Room` };
}
