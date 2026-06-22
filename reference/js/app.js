import { LEVEL_LABELS, accumulate, summarize } from "./board.js";

const summaryEl = document.querySelector("#summary");
const meterEl = document.querySelector("#meter");
const ledgerBody = document.querySelector("#ledger tbody");
const errorBox = document.querySelector("#error");

function showError(message) {
  errorBox.hidden = false;
  errorBox.textContent = message;
}

const usd = (n) => `$${n.toFixed(2)}`;
const tokens = (n) => n.toLocaleString("en-US");

function renderSummary(rows, summary, budget) {
  summaryEl.textContent =
    `${summary.turns} turns · ${tokens(summary.totalTokens)} / ${tokens(budget.maxTokens)} tokens · ` +
    `${usd(summary.totalCost)} · ${summary.toolCalls} tool calls · ${summary.retries} retries · ` +
    `${summary.compactions} compactions · ${LEVEL_LABELS[summary.level]}`;
}

function renderMeter(summary) {
  const width = Math.min(summary.pct, 100);
  meterEl.className = `meter level-${summary.level}`;
  meterEl.innerHTML = `<span class="bar" style="width:${width}%"></span><span class="pct">${summary.pct}% of budget</span>`;
}

function renderLedger(rows) {
  ledgerBody.innerHTML = rows.map((row) => `
    <tr class="level-${row.level}">
      <td>${row.turn}</td>
      <td>${row.label}</td>
      <td class="num">${tokens(row.tokens)}</td>
      <td class="num">${tokens(row.cumulativeTokens)}</td>
      <td class="num">${usd(row.cumulativeCost)}</td>
      <td class="num">${row.toolCalls ?? 0}</td>
      <td class="num">${row.retries ?? 0}</td>
      <td><span class="badge level-${row.level}">${LEVEL_LABELS[row.level]}</span></td>
    </tr>
  `).join("");
}

async function load() {
  try {
    const [budget, ledger] = await Promise.all([
      fetch("data/budget.json").then((r) => r.json()),
      fetch("data/usage.json").then((r) => r.json())
    ]);
    const rows = accumulate(ledger.turns, budget);
    const summary = summarize(ledger.turns, budget);
    renderSummary(rows, summary, budget);
    renderMeter(summary);
    renderLedger(rows);
  } catch (cause) {
    showError("Could not load cost data. Serve the folder so the data/ files resolve.");
  }
}

load();
