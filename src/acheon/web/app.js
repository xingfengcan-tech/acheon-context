const elements = {
  runtimeState: document.querySelector("#runtime-state"),
  runtimeLabel: document.querySelector("#runtime-label"),
  query: document.querySelector("#query"),
  namespace: document.querySelector("#namespace"),
  budget: document.querySelector("#budget"),
  budgetValue: document.querySelector("#budget-value"),
  httpToken: document.querySelector("#http-token"),
  seed: document.querySelector("#seed-button"),
  compile: document.querySelector("#compile-button"),
  ask: document.querySelector("#ask-button"),
  note: document.querySelector("#action-note"),
  receiptEmpty: document.querySelector("#receipt-empty"),
  receiptContent: document.querySelector("#receipt-content"),
  usageRing: document.querySelector("#usage-ring"),
  usagePercent: document.querySelector("#usage-percent"),
  usageCopy: document.querySelector("#usage-copy"),
  selectedCount: document.querySelector("#selected-count"),
  policyValue: document.querySelector("#policy-value"),
  auditValue: document.querySelector("#audit-value"),
  digestValue: document.querySelector("#digest-value"),
  traceCount: document.querySelector("#trace-count"),
  traceList: document.querySelector("#trace-list"),
  modelOutput: document.querySelector("#model-output"),
  packetOutput: document.querySelector("#packet-output"),
};

let runtime = { preview_only: true, model: "gpt-5.6-sol" };

function setBusy(active) {
  [elements.seed, elements.compile, elements.ask].forEach((button) => {
    button.disabled = active;
  });
}

function setNote(message, isError = false) {
  elements.note.textContent = message;
  elements.note.classList.toggle("error", isError);
}

function requestPayload() {
  return {
    query: elements.query.value.trim(),
    namespace: elements.namespace.value.trim() || "demo",
    budget_tokens: Number(elements.budget.value),
    scopes: ["global"],
  };
}

async function api(path, payload) {
  const headers = payload ? { "Content-Type": "application/json" } : {};
  const token = elements.httpToken.value.trim();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, {
    method: payload ? "POST" : "GET",
    headers,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.message || body.error || `Request failed (${response.status})`);
  }
  return body;
}

function shortHash(value) {
  if (!value) return "—";
  return value.length > 20 ? `${value.slice(0, 10)}…${value.slice(-8)}` : value;
}

function renderPacket(packet) {
  const usage = packet.budget_tokens
    ? Math.min(100, Math.round((packet.used_tokens / packet.budget_tokens) * 100))
    : 0;
  elements.receiptEmpty.classList.add("hidden");
  elements.receiptContent.classList.remove("hidden");
  elements.usageRing.style.setProperty("--usage", `${usage * 3.6}deg`);
  elements.usagePercent.textContent = `${usage}%`;
  elements.usageCopy.textContent = `${packet.used_tokens} / ${packet.budget_tokens}`;
  elements.selectedCount.textContent = String(packet.selected_ids.length);
  elements.policyValue.textContent = packet.policy_version;
  elements.auditValue.textContent = shortHash(packet.audit_head);
  elements.auditValue.title = packet.audit_head;
  elements.digestValue.textContent = shortHash(packet.digest);
  elements.digestValue.title = packet.digest;
  try {
    elements.packetOutput.textContent = JSON.stringify(JSON.parse(packet.context), null, 2);
  } catch (_error) {
    elements.packetOutput.textContent = packet.context;
  }

  elements.traceList.replaceChildren();
  elements.traceCount.textContent = `${packet.decisions.length} records considered`;
  packet.decisions.forEach((decision) => {
    const card = document.createElement("article");
    card.className = `trace-card${decision.selected ? " selected" : ""}`;

    const icon = document.createElement("span");
    icon.className = "trace-icon";
    icon.textContent = decision.selected ? "+" : "−";

    const content = document.createElement("div");
    const title = document.createElement("div");
    title.className = "trace-title";
    const name = document.createElement("strong");
    name.textContent = decision.record_id;
    name.title = decision.record_id;
    const tokens = document.createElement("span");
    tokens.textContent = `${decision.token_cost} est. tok`;
    title.append(name, tokens);

    const reasons = document.createElement("div");
    reasons.className = "reason-list";
    decision.reason_codes.forEach((reason) => {
      const tag = document.createElement("em");
      tag.textContent = reason;
      reasons.append(tag);
    });
    content.append(title, reasons);
    card.append(icon, content);
    elements.traceList.append(card);
  });
}

function renderModel(modelRun) {
  elements.modelOutput.classList.toggle("preview", modelRun.preview_only);
  elements.modelOutput.replaceChildren();
  const banner = document.createElement("p");
  banner.className = "mode-banner";
  banner.textContent = modelRun.preview_only
    ? `${modelRun.model} · preview only`
    : `${modelRun.model} · ${modelRun.status}`;
  const copy = document.createElement("p");
  copy.textContent = modelRun.preview_only
    ? "No API credential was used. The request was prepared locally, and no online answer was generated."
    : modelRun.output_text ||
      (modelRun.status === "completed"
        ? "The provider completed without text output."
        : `The provider returned status ${modelRun.status} without text output.`);
  elements.modelOutput.append(banner, copy);
}

async function refreshHealth() {
  try {
    runtime = await api("/health");
    elements.runtimeState.className = "runtime-state ready";
    elements.runtimeLabel.textContent = runtime.preview_only
      ? `${runtime.model} · preview only`
      : `${runtime.model} · online ready`;
  } catch (error) {
    elements.runtimeState.className = "runtime-state error";
    elements.runtimeLabel.textContent = "runtime unavailable";
  }
}

elements.budget.addEventListener("input", () => {
  elements.budgetValue.value = elements.budget.value;
  elements.budgetValue.textContent = elements.budget.value;
});

elements.seed.addEventListener("click", async () => {
  setBusy(true);
  try {
    const result = await api("/api/seed", { namespace: requestPayload().namespace });
    setNote(`${result.added.length} records added; ${result.skipped.length} already present.`);
  } catch (error) {
    setNote(error.message, true);
  } finally {
    setBusy(false);
  }
});

elements.compile.addEventListener("click", async () => {
  setBusy(true);
  try {
    const packet = await api("/api/compile", requestPayload());
    renderPacket(packet);
    setNote(`Packet compiled locally with ${packet.selected_ids.length} selected records.`);
  } catch (error) {
    setNote(error.message, true);
  } finally {
    setBusy(false);
  }
});

elements.ask.addEventListener("click", async () => {
  setBusy(true);
  try {
    const result = await api("/api/ask", requestPayload());
    renderPacket(result.packet);
    renderModel(result.model_run);
    setNote(
      result.model_run.preview_only
        ? "Request preview prepared. No online result was claimed."
        : `Online response returned status ${result.model_run.status}.`
    );
  } catch (error) {
    setNote(error.message, true);
  } finally {
    setBusy(false);
  }
});

refreshHealth();
