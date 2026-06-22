import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { costOf, assess, accumulate, summarize, firstBreach, note } from "../js/board.js";

// --- Cost Control Room pure functions ---------------------------------------
// The token-budget monitor itself is tested in tests/test_budget.py (the monitor
// runs on the Antigravity SDK, which is Python). These tests cover the web
// dashboard's pure roll-up helpers and the compaction-observability note.

const BUDGET = { maxTokens: 200000, warnAtTokens: 150000, maxTurns: 16, usdPer1kTokens: 0.005 };

async function ledger() {
  return JSON.parse(await readFile(new URL("../data/usage.json", import.meta.url), "utf8")).turns;
}

// --- Token accounting -------------------------------------------------------

test("costOf converts tokens to dollars at the configured rate", () => {
  assert.equal(costOf(200000, 0.005), 1);
  assert.equal(costOf(0, 0.005), 0);
});

test("assess classifies ok / warn / over", () => {
  assert.equal(assess(10000, BUDGET).level, "ok");
  assert.equal(assess(160000, BUDGET).level, "warn");
  assert.equal(assess(200000, BUDGET).level, "over");
});

// --- Ledger roll-up ---------------------------------------------------------

test("accumulate produces running cumulative totals", async () => {
  const rows = accumulate(await ledger(), BUDGET);
  assert.equal(rows[rows.length - 1].cumulativeTokens, 181000);
});

test("summarize totals the ledger", async () => {
  const summary = summarize(await ledger(), BUDGET);
  assert.equal(summary.totalTokens, 181000);
  assert.equal(summary.retries, 11);
  assert.equal(summary.compactions, 2);
  assert.equal(summary.level, "warn");
});

test("firstBreach is -1 while the build stays under the cap", async () => {
  assert.equal(firstBreach(await ledger(), BUDGET), -1);
});

// --- Compaction observability ----------------------------------------------

test("the compaction note reports the trigger", () => {
  assert.match(note({ trigger: "manual" }).systemMessage, /manual/);
  assert.match(note({ trigger: "auto" }).systemMessage, /automatic/);
});
