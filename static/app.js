const state = { user: "david.drm@demo", users: [], case: null, signals: [], audit: [], library: null };
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "X-Demo-User": state.user, ...(options.headers || {}) },
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || data.error || "Request failed");
  return data;
}

function chip(text, color) {
  return `<span class="chip ${color}">${text}</span>`;
}

function shortHash(hash) {
  return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
}

async function load() {
  state.users = await api("/api/users");
  const signalData = await api("/api/signals");
  state.signals = signalData.snapshots;
  const cases = await api("/api/cases");
  state.case = cases.cases[0];
  const audit = await api(`/api/cases/${state.case.id}/audit`);
  state.audit = audit;
  state.library = await api("/api/library");
  render();
}

function renderUsers() {
  $("user").innerHTML = state.users.map(u =>
    `<option value="${u.email}">${u.display_name} - ${u.role}</option>`
  ).join("");
  $("user").value = state.user;
}

function render() {
  renderUsers();
  $("case-state").textContent = state.case.state;
  $("digest").textContent = `digest ${shortHash(state.case.digest)}`;
  $("summary-signals").textContent = state.signals.length;
  $("summary-blockers").textContent = state.case.tasks.filter(t => t.critical && t.state === "BLOCKED").length;
  $("summary-approvals").textContent = `${state.case.approvals.length}/3`;
  $("summary-exports").textContent = `${state.case.exports.length}/5`;
  renderSignals();
  renderCase();
  renderApprovals();
  renderExports();
  renderLibrary();
  renderAudit();
}

function renderSignals() {
  $("signal-list").innerHTML = state.signals.map(s => `
    <div class="card">
      ${chip(s.adapter, "green")} ${chip(s.freshness, "amber")}
      <h3>${s.payload.rule || s.payload.dataset || s.payload.hazard}</h3>
      <p>${s.endpoint_url}</p>
      ${s.payload.probability ? `<p><b>Probability:</b> ${s.payload.probability}</p>` : ""}
      ${s.payload.compound_signal ? `<p><b>Compound signal:</b> ${s.payload.compound_signal}</p>` : ""}
      <p class="hash">sha256 ${s.payload_sha256}</p>
      <p class="muted">Retrieved ${s.retrieved_at}; schema ${s.schema_ok ? "valid" : "invalid"}</p>
    </div>
  `).join("");
}

function renderCase() {
  const a = state.case.assessment;
  $("gates").innerHTML = `
    <p>${chip(a.stage.toUpperCase(), "amber")} Probability ${a.probability}</p>
    ${a.gates.map(g => `<p>${chip(g.passed ? "PASS" : "FAIL", g.passed ? "green" : "red")} <b>${g.name}</b><br><span class="muted">${g.basis}</span></p>`).join("")}
    <p><b>Net benefit:</b> USD ${a.expected_avoidable_loss.net_benefit_usd.toLocaleString()}</p>
    <p class="hash">policy ${a.policy_hash}</p>
    <div class="assist"><b>Evidence Explainer</b><p>ICPAC/replay evidence crosses the GO threshold. Readiness was blocked until the transport task was resolved. The assist text is constrained to the deterministic policy trace.</p></div>
  `;
  $("cards").innerHTML = [
    ...a.eligible_cards.map(c => `<div class="card">${chip(c.stage.toUpperCase(), "green")}<h3>${c.title}</h3><p>${c.budget}</p><p class="muted">Owner: ${c.owner_role}</p></div>`),
    ...a.ineligible_cards.map(c => `<div class="card">${chip("INELIGIBLE", "red")}<h3>${c.title}</h3><p>${c.reason}</p></div>`)
  ].join("");
  $("tasks").innerHTML = state.case.tasks.map(t => `
    <div class="row">
      <b>${t.task}</b>
      <span>${t.owner_role}</span>
      <span>${t.critical ? chip("critical", "red") : chip("normal", "blue")}</span>
      <span>${chip(t.state, t.state === "BLOCKED" ? "red" : t.state === "RESOLVED" ? "green" : "blue")} ${t.blocker_code || ""}</span>
      <button ${t.state !== "BLOCKED" ? "disabled" : ""} onclick="resolveTask('${t.id}')">Resolve</button>
    </div>
  `).join("");
  const blocked = state.case.tasks.some(t => t.critical && t.state === "BLOCKED");
  $("send-review").disabled = state.case.state !== "ASSESSED" || blocked;
  $("send-review").className = !blocked && state.case.state === "ASSESSED" ? "primary" : "";
  $("review-message").textContent = blocked
    ? "Blocked: resolve all critical readiness tasks before review."
    : state.case.state === "ASSESSED" ? "Ready to send for review." : "Case is in review or later.";
}

function renderApprovals() {
  const roles = state.case.signatures_required;
  const currentUser = state.users.find(u => u.email === state.user);
  $("approval-list").innerHTML = roles.map(role => {
    const approval = state.case.approvals.find(a => a.role === role);
    const canApprove = currentUser && currentUser.role === role && state.case.state === "READY_FOR_REVIEW";
    return `<div class="card">
      <h3>${role}</h3>
      <p>${approval ? chip("Approved", "green") : chip("Awaiting", "amber")}</p>
      ${approval ? `<p>${approval.signer}<br><span class="hash">${approval.signature}</span></p>` : ""}
      <button class="primary" ${!canApprove ? "disabled" : ""} onclick="approve()">Approve & sign</button>
      ${!approval && !canApprove ? `<p class="muted">Switch to this role while the case is ready for review.</p>` : ""}
    </div>`;
  }).join("");
}

function renderExports() {
  const exports = Object.fromEntries(state.case.exports.map(e => [e.kind, e]));
  const kinds = [
    ["packet", "Activation Decision Packet"],
    ["cap", "CAP 1.2 alert"],
    ["husika", "Husika-ready payload"],
    ["bundle", "Air-gapped field bundle"],
  ];
  $("export-list").innerHTML = kinds.map(([kind, label]) => {
    const exp = exports[kind];
    return `<div class="card">
      <h3>${label}</h3>
      <p>${kind === "cap" ? chip("Exercise", "amber") : chip("Generated only", "blue")}</p>
      ${exp ? `<p class="hash">${exp.sha256}</p><a href="${exp.url}">Download ${exp.filename}</a>` : ""}
      <p><button ${!["APPROVED", "HANDED_OFF"].includes(state.case.state) ? "disabled" : ""} onclick="makeExport('${kind}')">Generate</button></p>
    </div>`;
  }).join("") + `
    <div class="card">
      <h3>CAP 1.2 cancellation</h3>
      <p>${chip("Stop trigger", "red")}</p>
      ${exports["cap-cancel"] ? `<p class="hash">${exports["cap-cancel"].sha256}</p><a href="${exports["cap-cancel"].url}">Download ${exports["cap-cancel"].filename}</a>` : ""}
      <p><button ${state.case.state !== "REVOKED" ? "disabled" : ""} onclick="makeExport('cap-cancel')">Generate cancellation</button></p>
    </div>
    <div class="card">
      <h3>Partner handoff control</h3>
      <p>${chip(state.case.state, state.case.state === "REVOKED" ? "red" : state.case.state === "HANDED_OFF" ? "green" : "amber")}</p>
      <p><button ${state.case.state !== "APPROVED" || !state.case.exports.length ? "disabled" : ""} onclick="markHandoff()">Mark handed off</button></p>
      <p><button ${!["APPROVED", "HANDED_OFF"].includes(state.case.state) ? "disabled" : ""} onclick="triggerStop()">Simulate stop trigger</button></p>
    </div>`;
  const base = `/integration/v1/activations/${state.case.id}`;
  $("integration").innerHTML = [base, `${base}/cap.xml`, `${base}/husika-payload.json`, `${base}/verify`, "/integration/v1/docs"]
    .map(url => `<p><code>${url}</code> <a href="${url}" target="_blank" rel="noreferrer">open</a></p>`).join("");
}

function escapeHtml(value) {
  return value.replace(/[&<>"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[char]));
}

function renderLibrary() {
  $("library-hash").textContent = `policy sha256 ${state.library.policy_sha256}`;
  $("policy-text").textContent = state.library.policy;
  $("actions-library").innerHTML = state.library.actions.map(action => `
    <article class="card">
      <h3>${action.id}</h3>
      <p class="hash">sha256 ${action.sha256}</p>
      <pre>${escapeHtml(action.content)}</pre>
    </article>
  `).join("");
}

function renderAudit() {
  $("chain").innerHTML = state.audit.chain.ok
    ? `<p>${chip("hash chain intact", "green")} ${state.audit.chain.events} events</p>`
    : `<p>${chip("hash chain broken", "red")} first broken seq ${state.audit.chain.broken_seq}</p>`;
  $("audit-list").innerHTML = state.audit.events.map(e => `
    <div class="event">
      <b>#${e.seq} ${e.event_type}</b> <span class="muted">${e.actor} at ${e.at}</span>
      <p class="hash">${e.this_hash}</p>
    </div>
  `).join("");
}

async function resolveTask(id) {
  await api(`/api/cases/${state.case.id}/tasks/${id}/resolve`, { method: "POST" });
  await load();
}

async function sendReview() {
  try {
    await api(`/api/cases/${state.case.id}/send-review`, { method: "POST" });
    await load();
  } catch (err) {
    $("review-message").textContent = err.message;
  }
}

async function approve() {
  await api(`/api/cases/${state.case.id}/approve`, { method: "POST" });
  await load();
}

async function verifySignatures() {
  const result = await api(`/api/cases/${state.case.id}/verify-signatures`);
  $("signature-verification").innerHTML = `
    <article class="${result.ok ? "ok-panel" : "warn-panel"}">
      <h3>${result.ok ? "Signatures verified" : "Signatures incomplete"}</h3>
      <p class="hash">signed digest ${result.signed_digest || "pending"}</p>
      <div class="grid">
        ${result.roles.map(r => `<div>${chip(r.valid ? "valid" : "pending", r.valid ? "green" : "amber")} <b>${r.role}</b><br><span class="muted">${r.signer || "awaiting signer"}</span></div>`).join("")}
      </div>
    </article>
  `;
}

async function makeExport(kind) {
  await api(`/api/cases/${state.case.id}/exports/${kind}`, { method: "POST" });
  await load();
}

async function markHandoff() {
  await api(`/api/cases/${state.case.id}/mark-handoff`, { method: "POST" });
  await load();
}

async function triggerStop() {
  try {
    await api(`/api/cases/${state.case.id}/simulate-stop-trigger`, { method: "POST" });
    await load();
  } catch (err) {
    alert(err.message);
  }
}

document.querySelectorAll("nav button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button, .tab").forEach(el => el.classList.remove("active"));
    btn.classList.add("active");
    $(btn.dataset.tab).classList.add("active");
  });
});
$("user").addEventListener("change", async e => { state.user = e.target.value; await load(); });
$("seed").addEventListener("click", async () => { await api("/api/seed", { method: "POST" }); await load(); });
$("send-review").addEventListener("click", sendReview);
$("verify-signatures").addEventListener("click", verifySignatures);
load();
