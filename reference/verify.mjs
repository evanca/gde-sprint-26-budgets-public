import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";

const read = (rel) => readFile(new URL(rel, import.meta.url), "utf8");
const readJson = async (rel) => JSON.parse(await read(rel));

// --- App shell ---
const html = await read("./index.html");
const css = await read("./css/index.css");
assert.match(html, /id="summary"/, "summary element is required");
assert.match(html, /id="ledger"/, "ledger element is required");
assert.match(html, /id="meter"/, "budget meter element is required");
assert.match(css, /@media/, "responsive styles are required");

// --- Budget integrity ---
const budget = await readJson("./data/budget.json");
for (const key of ["maxTokens", "warnAtTokens", "usdPer1kTokens"]) {
  assert.equal(typeof budget[key], "number", `budget.${key} must be a number`);
}
assert.ok(budget.warnAtTokens < budget.maxTokens, "warnAtTokens must be below maxTokens");

// --- Usage ledger integrity ---
const ledger = await readJson("./data/usage.json");
assert.ok(Array.isArray(ledger.turns) && ledger.turns.length > 0, "usage.json needs a non-empty turns array");
for (const turn of ledger.turns) {
  assert.equal(typeof turn.turn, "number", "each turn needs a turn number");
  assert.equal(typeof turn.tokens, "number", `turn ${turn.turn} needs numeric tokens`);
}

// --- Monitor present: the token-budget logic lives in monitor/budget.py ---
// (The monitor is exercised by tests/test_budget.py; the SDK wiring is
// monitor/agent.py. Both are Python — the Antigravity SDK is Python.)
const monitor = await read("./monitor/budget.py");
assert.match(monitor, /def update\(/, "monitor/budget.py must export an update() monitor");
assert.match(monitor, /def decide\(/, "monitor/budget.py must export a deny-all decide()");

console.log("Static verification passed.");
