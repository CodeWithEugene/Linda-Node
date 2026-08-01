<p align="center">
  <img src="docs/brand/linda-node-logo-horizontal.png" alt="Linda Node" width="360" />
</p>

<h1 align="center">4-minute demo script</h1>

<p align="center">
  <strong>URL:</strong> <code>https://linda-node.vercel.app</code> · <strong>password for every persona:</strong> <code>linda-demo</code>
</p>

---

## Before you start (2 minutes, off camera)

1. Open **three browser windows** side by side, each signed in as a different persona — this is the single biggest time-saver in the whole demo, because the approval beat needs three identities and re-logging in costs you 40 seconds you do not have.
   - Window **A** → `david.drm@demo` (County DRM Officer) — your main window
   - Window **B** → `amina.ews@demo` (EWS Specialist)
   - Window **C** → `grace.ngo@demo` (NGO & Finance Lead)
2. In **Window A**, sit on the landing page (`/`) with the map loaded.
3. In **Window B and C**, pre-navigate to `/cases/case_ruvuma_ond2026?tab=approvals`.
4. Have a fourth tab ready on `https://linda-node.vercel.app/integration/v1/docs`.
5. If anything looks stale, sign in as `admin@demo` and hit **Restore seed data**, then **Refresh** on the landing page. Takes about 10 seconds.

**Numbers you should know cold:** 214 admin-1 units · 11 countries · 3 activating · Ruvuma 51.8 % · 13 forecast issues available.

## 0:00 – 0:12 · Help and accessibility

**Screen:** the landing page, before beginning the main story.

> "Before we get into the workflow, the two controls in the lower-right keep the workspace usable for more people. The upper chat icon opens Linda Guide directly above the button: ask how the workspace handles evidence, cases, approvals, sources, and accessibility. It uses curated product knowledge and gives bounded product guidance rather than operational or emergency advice."

*(Click the chat icon, ask “How do approvals work?”, then close it.)*

> "The accessibility icon saves personal display preferences on this device: larger text, higher contrast, and reduced motion. The underlying interface also supports keyboard navigation and screen readers — these controls are preferences, not a substitute for accessible design."

*(Click the accessibility icon, enable **Larger text** briefly, then switch it back off before the rest of the demo.)*

> "Inside a decision case, three optional NVIDIA NIM assists can explain already-recorded evidence, re-rank only policy-eligible actions, or suggest a blocker code. Every answer is schema-validated and advisory: it cannot change an assessment, approval, task, or decision."

---

## 0:00 – 0:35 · The gap

**Screen:** the landing page, Regional Readiness, map visible.

> "Early warning in the Greater Horn of Africa is not broken. ICPAC already runs the forecasting, the trigger platform, and — through Husika — SMS, USSD, and mobile delivery to the last mile.
>
> The gap is what happens *between* a threshold being crossed and a funded action actually starting. Which pre-agreed action begins, who approves it, what evidence justifies it, and can anyone prove it afterwards?
>
> ICPAC's own trigger engine shows the shape of the gap exactly. It has two action types: send an email, and update a dashboard."

*(Click **Signal Inbox** in the left nav, point at the "ICPAC trigger actions" card showing `email_alert` and `dashboard_update`.)*

> "That is read live from their `/api/triggers/actions/` endpoint right now. **Linda Node is the third action type: governed activation.**"

---

## 0:35 – 1:20 · Live, and honest about it

**Screen:** click **Regional Readiness** to go back to `/`.

> "This is not a prepared scenario. Every admin-1 unit ICPAC publishes statistics for — **214 units across all 11 countries** — assessed against the same versioned policy, right now, on the OND 2026 seasonal forecast."

*(Point at the stat tiles.)*

> "Three units reach a stage. Which means **211 do not** — and Linda Node says so."

*(Click the **All 214** toggle. Let the list scroll for two seconds. Then click **Reaching a stage** to go back.)*

> "That matters more than it sounds. The normal output of an activation system is *no activation recommended*. A system that can't say that calmly can't be trusted the day it does recommend action. Most demos you'll see today invent an emergency. This one reports what the data actually says."

*(Hover one coloured polygon on the map so the tooltip appears.)*

> "The map is ICPAC's own GADM vector tiles from their tile server, joined to their statistics on the same `gid_1` identifier. No geometry of our own."

---

## 1:20 – 1:55 · Multi-hazard, using their science

**Screen:** still on the ranking. Point at the three activating rows.

> "Ruvuma in Tanzania is at **SET** — 51.8 % exceedance, real recorded ICPAC data. Mtwara is at READY.
>
> Now look at the third row. **Bungoma, Kenya** — drought probability essentially zero, but it's at READY via the **heat** policy."

*(Point at "via heat policy".)*

> "That comes from ICPAC's own live trigger rule for Bungoma — a max-temperature rule someone at ICPAC configured. And here's the constraint that shaped our architecture:"

*(Click **Policy & Actions** → **ICPAC indicators** tab.)*

> "Their indicator registry says only SPI-3 CHIRPS supports forecasting. TMAX and rainfall are monitoring-only. So heat readiness *cannot* be probability-driven.
>
> We did not invent a heat severity model to paper over that. The heat policy maps **ICPAC's own `severity_level`** onto a readiness stage. We consume their science; we never replace it."

---

## 1:55 – 2:50 · The governed decision

**Screen:** Window A → **Decision Cases** → open **OND 2026 drought — Ruvuma, Tanzania** (the `ASSESSED` one).

*(Land on the **Evidence** tab.)*

> "Open a case and you get the full trace. Every gate, pass or fail. The stage conditions with the observed value. And the cost–loss calculation — expected avoidable loss of about **$392,000** against a readiness cost of **$39,500**."

*(Point at the coloured provenance chips under the formula.)*

> "Every operand is labelled: green is an official source, amber is an assumption written into the reviewed policy file. Nothing is unattributed."

*(In the **AI evidence explanation** panel, click **Run explainer** and wait for the grounded response.)*

> "The explainer reads only this recorded evidence trace and returns the snapshot IDs it cited. It has a 30-second response window because NVIDIA may retry a malformed structured response once; it is still advisory and cannot change policy, gates, approvals, tasks, or the case state."

*(Click **Actions & Readiness**.)*

> "Three action cards are eligible. Seed distribution is **not** — it needs 120 days of lead time and we have 90. The engine says exactly why."

*(Point at the red sticky bar at the bottom.)*

> "And this case cannot move. A critical task — transport contracts — is blocked. Watch."

*(Switch to **Window C, Grace**. She's already on the case. Go to Actions & Readiness → **Update** on `Transport contracts confirmed` → **Resolve** → Save.)*

*(Back to **Window A, David**. Refresh. The bar is green.)*

> "Now it can go for review."

*(Click **Send for review**.)*

---

## 2:50 – 3:25 · Three signatures

**Screen:** Window B (Amina) → **Approve & sign** → tick the box → Confirm.

> "Anticipatory action is never one person's call. Three distinct roles co-sign: the climate specialist, the county officer, and the financing lead."

*(Window A, David → Approvals → **Approve & sign** → Confirm.)*

*(Window C, Grace → **Approve & sign** → Confirm. The case flips to APPROVED.)*

> "Three signatures, and only three signatures, produce an approval. Each one is an HMAC over a canonical snapshot of the case."

*(Expand **Verify signatures**.)*

> "All three cover the same digest — you can verify that live. This is integrity protection within the system, with server-held keys. It's a signed decision record. It is not PKI and it is not a blockchain, and we won't call it that."

---

## 3:25 – 3:50 · Artifacts and interoperability

**Screen:** Window A → **Handoffs & Exports**.

*(Click **Generate** on the CAP card, then on the Husika card.)*

> "Approval unlocks four artifacts. A signed decision packet as PDF and hashed JSON. A **CAP 1.2 alert** validated against the OASIS schema. A **Husika payload** validated against Husika's own published OpenAPI contract — we never call their write endpoint, this is ready for an authorised operator. And an air-gapped ZIP for a county office with no connectivity."

*(Switch to the pre-opened `/integration/v1/docs` tab.)*

> "And integration runs both ways. We validate against their schema — and we publish one they could consume: a public CAP feed, a versioned REST API, and signed webhooks."

---

## 3:50 – 4:00 · Close

**Screen:** back to Regional Readiness (`/`).

> "Linda Node doesn't replace Husika and it doesn't replace ICPAC's science. It's the governed layer between them — so that when a threshold is crossed, there's a defensible answer to *what happens next, who owns it, and what proves it.*
>
> Built entirely on ICPAC's open APIs. Thank you."

---

## If you have 30 seconds spare

Sign in as `admin@demo` → **Stop-trigger evaluation**, pick the handed-off case, enter `0.55` → Evaluate.

> "Above the policy threshold, nothing happens — but the evaluation is still recorded."

Then enter `0.22` → Evaluate. The case revokes.

> "Below it, the policy revokes the activation and a CAP Cancel becomes available. It's a condition, not a button."

---

## Recovery

| If this happens | Do this |
|---|---|
| A case is in the wrong state | `admin@demo` → **Restore seed data** (~10 s) |
| The map doesn't paint | Ignore it and talk over the ranking — it's the same data, and the map warns you itself |
| Data looks stale | **Refresh** on the landing page |
| You lose a login | The two finished cases — one `HANDED_OFF` with all four exports, one `REVOKED` — are already seeded. Show those instead |

## Things to say precisely

| Say | Never say |
|---|---|
| "a cryptographically signed decision record (HMAC)" | "PKI", "digital signature", "blockchain" |
| "records the recommended release for human authorisation" | "releases $18,000" |
| "validates against Husika's published schema, ready for an authorised operator" | "integrates with Husika" |
| "signal overlap detection" | "compound hazard index" |
| "a team-authored demonstration policy" | "ICPAC's thresholds" or "official policy" |
| "no activation recommended" | anything that implies a stage where none was reached |
