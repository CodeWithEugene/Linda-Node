# Linda Node: Hackathon Research, Competitive Audit, and Build Recommendation

**Prepared:** 22 July 2026 (EAT)  
**Decision:** Do **not** build Linda Node as another last-mile alerting app, chatbot, Telegram bot, USSD/SMS product, PWA, or community-feedback map. Those are already central to Husika and, in several cases, to the ICPAC Triggers & Thresholds platform. Build a complementary **decision-to-action control plane**: an auditable, human-governed workspace that turns an ICPAC forecast/trigger into a localized, pre-agreed action recommendation, evidence packet, assignment/acknowledgement workflow, and Husika-ready communication handoff.

The working product name in this report is **Linda Protocol**. "Linda" still means protect, but the product protects decision quality and execution readiness rather than trying to replace ICPAC's channel infrastructure.

> **One-sentence pitch:** Linda Protocol is the transparent activation desk between ICPAC's trigger data and Husika's communication channels: it proves *why* a location needs action, *which pre-agreed action* is appropriate, *who must approve and execute it*, and *what is blocking readiness*—without letting an LLM or a demo heuristic authorize finance.

## 1. Executive decision

The current README has a serious positioning collision. It proposes a multi-channel early-warning delivery layer (Telegram, SMS, USSD, PWA/APK), multilingual advice, geo-targeting, approval-like flows, and crowdsourced community reports. Husika publicly presents each of these as existing product capability: SMS/USSD, Android/iOS/web, offline support, geo-targeting, multilingual rich media, approval workflows, delivery confirmation, and feedback. ICPAC also publicly says it is planning local-language Gemini conversational reporting with Husika. A technically literate ICPAC judging panel will see a last-mile delivery/chatbot pitch as a rebuild of its own systems rather than a useful extension.

The real, policy-backed gap is the operational bridge from **forecast/trigger → likely impact → pre-agreed action → accountable approval/execution → evidence of what happened**. IGAD's AA roadmap identifies fragmented risk data, lack of impact-based forecasting models, limited operational capacity, agency-specific action plans, disconnected finance arrangements, and the lack of consolidated AA information as regional problems. It calls for harmonised trigger approaches, information management, and a platform communicating triggers/thresholds and actions activated. That is a much sharper problem than "people need an app."

### Recommendation in one table

| Decision | Recommendation | Why it wins with this panel |
|---|---|---|
| Product category | **Decision-to-action / activation-readiness control plane** | Complements, rather than competes with, Husika and ICPAC's existing public platforms. |
| Primary user | County disaster/early-warning officer plus NGO AA programme manager | They own the decision bottleneck; community users continue to receive information through Husika. |
| Demo hazard | Start with **drought or flood replay**, but make the data adapter generic | ICPAC has public drought/heat/flood surfaces; use one polished flow, not a nominal multi-hazard claim. |
| Data basis | ICPAC Triggers & Thresholds API + official boundary IDs + versioned local replay fixture | Demonstrates real integration while remaining robust if a live public endpoint changes. |
| AI role | Structured evidence explanation, approved-action retrieval, and blocker classification only | Earns AI creativity points without allowing hallucinations to decide triggers, eligibility, or money. |
| Human authority | Named approver confirms a recommendation; no automatic fund release or alert dispatch | Mirrors AA governance and prevents an unsafe "AI releases relief funds" claim. |
| Husika relationship | **Handoff/integration boundary, not replacement** | Makes the project adoptable by ICPAC; do not claim a private Husika API exists until ICPAC provides one. |

## 2. Research method and evidence standard

This report reviewed the local repository, live Devpost pages, the public Husika site and app-store listings, ICPAC public news/training/policy material, the public Thresholds & Triggers API/tile service, and **all 65 public, non-archived repositories** returned by the public `icpac-igad` GitHub-organisation API. Sources were checked on 22 July 2026 unless another date is stated. A public repository can be incomplete, stale, or only one component of a privately operated system; “not seen publicly” is never treated as proof that a capability does not exist.

Evidence labels are deliberate:

- **Verified** — observed in a live official page/API, an app-store record, or a public repository/file.
- **Publicly unverified** — not visible in the inspected public surfaces; this does **not** prove it does not exist internally.
- **Inference** — a reasoned recommendation from verified evidence, clearly not a claim about ICPAC's internal product roadmap.

This distinction matters: the judging panel includes ICPAC developers and will spot invented APIs, overstated integrations, or claims that a public platform "does not have" something merely because it is not documented.

## 3. The hackathon contract: what must be optimised

### Verified requirements and constraints

The Devpost overview asks for an innovative solution strengthening early warning, preparedness, resilience, or decision-making. Submission requires a project overview (maximum 250 words), solution details (maximum 250 words), working web application or APK, demonstration video (maximum five minutes), technology stack, and a GitHub link **where applicable**. The deadline is **31 July 2026, 17:00 EAT/GMT+3**. The top ten proceed to a physical evaluation workshop; Devpost's public copy does not state its venue or promise a live-demo format. A failure-resistant demo is nevertheless essential. See the [Devpost overview](https://igad-husika-hackathon.devpost.com/).

| Criterion | Weight | Practical implication |
|---|---:|---|
| Technical Depth & Engineering | 30% | Show a real source adapter, typed domain model, deterministic decision policy, reproducible replay, tests, provenance, and a graceful offline/failure path. |
| Innovation & AI Creativity | 30% | AI must do more than paraphrase weather. Use it to make governed evidence legible and to constrain decision workflow, while retaining deterministic gates. |
| Problem Value & Impact | 25% | Tie the product to a named AA operating failure: decision readiness and coordinated action, not generic “last mile.” Define measurable time/quality metrics. |
| Presentation & Documentation | 15% | Give judges a concise narrative, live proof, assumptions, limits, and a 5-minute arc that does not depend on a cloud service behaving perfectly. |

The rules require original work, disclosure/acknowledgement of external tools/data/APIs, a maximum of five team members, and evaluate innovation, impact, technical quality, user experience, and scalability. They also explicitly warn that organisers may independently develop similar solutions; differentiation must be concrete rather than ownership-based. See [rules](https://igad-husika-hackathon.devpost.com/rules).

### Competition intelligence

- The public gallery is currently unpublished, so there is no trustworthy public competitor set to reverse-engineer. The overview showed 344 participants during research. Do not invent a competitor analysis; instead design against the incumbent ICPAC stack. See [gallery](https://igad-husika-hackathon.devpost.com/project-gallery).
- The resources page explicitly names Husika, Hazard Watch, Drought Watch, and Thresholds & Triggers as reference systems. A solution that ignores them—or reconstructs them—will look less aligned than one that extends them. See [resources](https://igad-husika-hackathon.devpost.com/resources).
- **Eligibility caveat:** the public location selector and a forum response appear inconsistent about South Sudan. Treat Devpost's currently configured eligibility as controlling and ask `hackathon@icpac.net` if any member's eligibility depends on the discrepancy. This is operational housekeeping, not a product risk.

### What the panel composition implies

The listed judges include ICPAC's lead developer Jason Kinyua, ICPAC developer Mohammed Ali, ICPAC GIS developer Crimson Sikolia, plus developers from Bunifu Technologies—the company publicly named as Husika's developer. This increases the premium on exact source attribution, credible geospatial/data handling, thoughtful failure modes, and a clear non-duplication story. The strongest sentence to say in the demo is:

> “We deliberately did not build a second Husika. We built the governed activation layer that gives Husika, county teams, and financing partners a shared answer to: *what should happen next, who owns it, and what evidence supports it?*”

## 4. What already exists: the incumbent map

### 4.1 Husika already owns the last mile

**Verified:** Husika describes itself as a communication and feedback system for early warning, advisories, knowledge, and awareness. Its public documentation describes a four-level model from regional/national creation through country/sector tailoring and county/district distribution to community/individual feedback. It supports threats, forecasts, feeds, and follow-up messages; geographic, sector, and language targeting; approval workflows; SMS/USSD, mobile app, and web distribution; delivery/feedback analytics; and offline-capable rich mobile content. See [How Husika Works](https://husika.icpac.net/how-husika-works) and [Husika home](https://husika.icpac.net/).

**Verified:** Husika advertises Android, iOS, web, and a `*445#` USSD route. The Android listing identifies it as the official ICPAC app and was updated 4 May 2026; the iOS listing identifies bundle ID `com.husika.app`, version 1.2.1, with location-based alerts, threat alerts, emergency broadcasts, and local-language support. See [Google Play](https://play.google.com/store/apps/details?id=com.husika.app&hl=en) and [Apple App Store](https://apps.apple.com/ke/app/husika/id6748664825).

**Verified:** ICPAC's April 2026 Husika article says it already connects early-warning data, disaster-risk information, and humanitarian updates; uses app/SMS/web feeds; localises messages; and supports two-way community feedback/local data. A 2025 ICPAC training manual likewise describes SMS delivery and recipient replies used to assess ground conditions/crowdsource data. See [ICPAC's Husika article](https://icpac.medium.com/husika-enabling-igad-member-states-reach-the-last-mile-with-actionable-early-warnings-11e8997a2ed4) and [training manual](https://www.icpac.net/documents/1040/Final_Training_Manual_Booklet_copy.pdf).

**Verified future direction:** ICPAC's 23 June 2026 cloud-modernisation article says it plans Gemini conversational interfaces in local languages and plans to combine that vision with Husika. Therefore a Gemini RAG chatbot offering personalised climate advice is not a defensible standalone wedge. See [ICPAC / Google Cloud article](https://www.icpac.net/news/icpac-strengthens-climate-services-delivery-with-90-faster-insights-on-google-cloud/).

**Consequence:** Remove from the core pitch: Telegram-first delivery, an Android/iOS/PWA replacement, generic multilingual Q&A, SMS/USSD onboarding, generic geo-targeted alerts, and "Community Sentinel" as a supposedly novel two-way feedback mechanism. They may remain an integration boundary or a demo stub, but they are not the innovation.

### 4.2 Thresholds & Triggers already owns a large part of trigger operation

**Verified:** The public Thresholds & Triggers system covers multi-hazard monitoring, seasonal forecasts, skill-calibrated triggers, forecast persistence, and country-to-ward analysis. Its public product page says it can automatically evaluate triggers and dispatch alerts when thresholds are exceeded, and describes exporting bulletins, triggering alerts, and activating anticipatory-action protocols. This is a warning against pitching a generic "trigger monitor" or an automatic alert dispatcher as novel. [Platform home](https://eatriggersthresholds.icpac.net/).

**Verified public technical surface (tested):**

| Surface | Demonstrated use in Linda Protocol |
|---|---|
| [`/api/datasets/`](https://eatriggersthresholds.icpac.net/api/datasets/) | Registry of categories, sources, seasons, indicators. Cache contract/version. |
| [`/api/datasets/indicators/`](https://eatriggersthresholds.icpac.net/api/datasets/indicators/) | Six indicators: SPI-3 CHIRPS/ERA5, SPEI-3, TMAX, TMIN, and rainfall; only SPI-3 CHIRPS declares seasonal forecast support. |
| [`/api/datasets/forecasts/available/?forecast_type=return_period`](https://eatriggersthresholds.icpac.net/api/datasets/forecasts/available/?forecast_type=return_period) | Current available seasonal forecast catalogue. At research time it included OND 2026, July issue, three-month lead. |
| [`/api/datasets/forecasts/seasons/?forecast_type=return_period`](https://eatriggersthresholds.icpac.net/api/datasets/forecasts/seasons/?forecast_type=return_period) | Valid season, lead, and forecast-init metadata. |
| [`/api/datasets/forecasts/stats/`](https://eatriggersthresholds.icpac.net/api/datasets/forecasts/stats/?admin_level=1&valid_date=2026-10-01&lead_months=3&min_probability=0&country=KEN) | Admin-level return-period probability statistics; use a documented query adapter rather than screen-scraping a map. |
| [`/api/areas/areas/`](https://eatriggersthresholds.icpac.net/api/areas/areas/?level=1&code=KEN&fields=id,name) | Canonical ICPAC/GADM-style admin identifiers and names. Use IDs as join keys. |
| [`/tileserv/index.json`](https://eatriggersthresholds.icpac.net/tileserv/index.json) | Public `pg_tileserv` catalogue with GADM admin levels 0–4, clusters, child-vulnerability layers, and flood grid. |

The APIs are publicly readable but not presented as a stable external developer contract. Treat them as an upstream dependency: define an adapter, validate schema, cache raw responses with their timestamp/hash, display freshness, and ship a versioned replay fixture. Do **not** promise a production SLA or unannounced private endpoint.

### 4.3 Policy makes the decision layer a real problem, not a hackathon invention

The [IGAD Regional Roadmap for Anticipatory Action](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf) describes AA as requiring: pre-existing needs-based action plans, forecasts with lead time and impact/affected-population information, co-production with stakeholders and indigenous knowledge, and pre-identified financing/arrangements. It identifies fragmented risk data, a lack of impact-based forecasting models, and insufficient capacity to operationalise them; it calls for harmonised triggers, an AA information-management system, and a regional platform communicating triggers/thresholds and actions activated.

The [Kenya AA Roadmap](https://www.icpac.net/documents/923/Kenya-Anticipatory-Action-Roadmap-2024-to-2029.pdf) defines a trigger as criteria for where/when funds or assistance are allocated based on threshold values and anticipated hazard, built from hazard, historical impact, and vulnerability analysis. This gives Linda Protocol a precise and defensible boundary: it makes the evidence and process legible; policy owners still determine the actual thresholds, action plans, and funding authorities.

### 4.4 ICPAC's public engineering estate: reuse the science; add the operational layer

The GitHub audit changes the recommendation from merely “better workflow” to a specific extension point that ICPAC's own public model documentation names. The [`bn-ibf` flood implementation](https://github.com/icpac-igad/bn-ibf) explicitly separates **Layer 1: probabilistic risk assessment** from **Layer 2: institutional decision/action**. Linda Protocol belongs in Layer 2. It must render and carry forward existing Layer-1 evidence—not recalculate a competing flood model or present a new climate algorithm as the innovation.

| Existing public capability | What the audit verified | Consequence for Linda Protocol |
|---|---|---|
| [CRMA web / `arco-ibf`](https://github.com/icpac-igad/arco-ibf/blob/cmra-web/README.md) | A current climate-risk-management application with historical events, storylines, monitoring, IBF views, maps, reports, admin-1 risk APIs, and an existing scenario-chat interface. Its upstream API is documented as private Cloud Run behind Next.js identity-token proxying. | Do not clone its map, dashboard, scenario narration, or chatbot. Use a pinned public artefact/replay fixture unless ICPAC authorises API access. |
| [`bn-ibf` flood pipeline](https://github.com/icpac-igad/bn-ibf/blob/jua-bnet/flood_ibf/flood_bn_ibf_system_v20260412.md) | Daily risk for 227 admin-1 regions in 11 countries, using antecedent rainfall, 51-member ECMWF ensemble information, CMORPH thresholds, and Julia/Python Bayesian-network outputs. | Do not pitch ensemble/tail-risk flood prediction as novel; ingest a published/sandboxed risk record or fixture. |
| [Risk/action boundary and cost-loss work](https://github.com/icpac-igad/bn-ibf/commit/9e080ee833413f7992124f6c3bc76eb2b3140f6f) | Deterministic CRMA states, traffic lights, explanations, 227×51 member evidence and a configurable cost-loss ratio already exist. | Do not claim cost-loss modelling is missing. Show its source/policy version, then connect it to authorised intervention runbooks, approvals, owners, and evidence. |
| [Soft evidence](https://github.com/icpac-igad/bn-ibf/commit/18ad13bfca10f8680e2bda4be067f5f2f7e9b43e) and [dynamic-BN/storyline](https://github.com/icpac-igad/bn-ibf/commit/969aba494fc46dffbaf124d2eb003ef2ae60e763) changes | The April 2026 technical critique's near-term gaps were subsequently implemented: soft evidence, temporal coupling, and automated worst/median/best storylines. | Never frame these algorithms as the team's missing breakthrough. Put uncertainty/storylines in an action case as source evidence. |
| [Exposure/impact integration](https://github.com/icpac-igad/bn-ibf/blob/jua-bnet/exposure/integrate_exposure_risk.py) | Offline code joins risk with WorldPop, INFORM vulnerability/lack-of-coping data, and optional OSM infrastructure to derive impact score/tier; the public CRMA client did not expose this as a public impact-score route. | A useful display seam is a traceable impact/evidence card, but use existing output where supplied; do not fabricate an “official” exposure score. |
| [`flood_watch_system`](https://github.com/icpac-igad/flood_watch_system/blob/main/README.md) | An operational East Africa Flood Watch stack already combines Django/Wagtail, Next.js, MapServer, MapCache, PostGIS, pg_tileserv, scheduled ingestion, hazard/rainfall/streamflow/population layers, and notifications. | No parallel flood GIS, WMS/WFS stack, or raw pipeline. Treat it as an upstream operational source subject to access approval. |
| [`ibf-thresholds-triggers`](https://github.com/icpac-igad/ibf-thresholds-triggers/blob/kmj/README.md), [`fast-cgan`](https://github.com/icpac-igad/fast-cgan), [`ea-aifs`](https://github.com/icpac-igad/ea-aifs/blob/main/README.md) | Existing drought-trigger, cGAN and AIFS forecast systems already cover probability thresholds, regional forecast APIs/UIs, and GPU ensemble processing. | No threshold calculator, cGAN/AIFS model, or raw GRIB download pipeline. |
| [`geoserve`](https://github.com/icpac-igad/geoserve/blob/main/README.md), [`stac-api`](https://github.com/icpac-igad/stac-api/blob/main/README.md), [`ea-impact-events`](https://github.com/icpac-igad/ea-impact-events/blob/main/README.md) | Reusable patterns/data for STAC provenance, raster/vector serving, and 448 geocoded flood/drought events at admin-2. The STAC sample catalogue has older dates; do not call it live without checking. | Use STAC-style source links/content hashes in the Decision Packet; do not make a catalogue or tile server the hackathon product. |

**Precise integration principle:** for a flood demo, represent a source record with CRMA state/posterior, cost-loss ratio or `C/L` value *as supplied*, impact tier, and three model storylines. Linda then resolves that evidence against a human-authored action policy and records the institutional outcome. If those source values cannot be lawfully fetched at run time, ship a labelled, pinned fixture containing the public provenance and a swappable connector. This is both technically honest and more robust than scraping a private application.

### 4.5 Adjacent platforms confirm the same boundary

ICPAC also operates [Drought Watch](https://droughtwatch.icpac.net/), [Hazards Watch](https://eahazardswatch.icpac.net/), and the public Triggers & Thresholds platform. Kenya's [NDMA drought-information service](https://ndma.go.ke/drought-information/) publishes national/county bulletins and recommended interventions; Kenya Red Cross has activated drought early-action protocols. These systems demonstrate that maps, bulletins, remote-sensing indicators, and intervention concepts already exist. The product opportunity is not another information portal. It is the cross-organisation operational thread—source evidence → approved policy → accountable action → blocker/escalation → outcome—that can travel through those systems.

This conclusion is reinforced by ICPAC's [IMPAACT announcement](https://www.icpac.net/news/action-against-hunger-and-the-igad-climate-prediction-and-applications-centre-icpac-launch-landmark-echo-funded-initiative-to-build-anticipatory-action-systems-across-the-greater-horn-of-africa/): Ethiopia, Somalia, and Djibouti work is focused on interoperable government-led AA systems, trigger-matrix validation, and rapid financing. Linda should make integration and governance easier; it must not pretend to replace this institutional programme.

## 5. Current Linda Node: what to retain, what to cut, what to reframe

| Existing README claim/component | Assessment | Action |
|---|---|---|
| Consume real ICPAC trigger data | Strong and still correct | Keep, but use an adapter with cache/replay, source freshness, raw evidence, and no claim that arbitrary heuristic thresholds are ICPAC policy. |
| GIS/admin-unit evidence | Strong | Keep, but use ICPAC area IDs/vector tiles; do not build a parallel geospatial data pipeline for the MVP. |
| Deterministic rules before LLM | Excellent | Make it the central trust principle. LLM cannot trigger, approve, allocate, or silently alter a policy. |
| Proof of Risk PDF | Directionally useful but too finance-forward | Rename as **Activation Decision Packet**. It documents an evidence chain and a human decision; it does not request, approve, or release funds. |
| Multi-agent monitor/context/router | Broad and duplicative | Replace with three narrow, constrained assists: Evidence Explainer, Approved-Action Matcher, and Feedback/Blocker Structurer. |
| Telegram/SMS/USSD/PWA/APK | High duplication with Husika | Remove from MVP. Model Husika as an approved downstream channel/handoff. |
| Community reports as novel "sentinel" layer | Existing Husika capability | Reframe as optional structured evidence input that is de-duplicated, provenance-labelled, and never sufficient on its own to fire a trigger. |
| Africa's Talking, Capacitor, bot frameworks | Extra integration surface with little differentiated value | Cut entirely from hackathon build. |
| Supabase/PostGIS, pgvector, bulletin RAG | More infrastructure than the wedge needs | Defer. Start with typed policy/action files and an audit database; add persistence only where it proves the workflow. |

The original document did one thing especially well: it recognised that warnings alone do not create action. Preserve that insight, but make the product the **operational evidence and coordination layer** rather than another warning channel.

## 6. The white space: narrow, defensible, and useful

### Verified versus not yet proven

| Capability | Public evidence | Position for Linda Protocol |
|---|---|---|
| Multi-channel dissemination, targeting, approval, delivery confirmation | Husika public site | Do not rebuild. |
| Community feedback/crowdsourcing | Husika/ICPAC public materials | Do not claim novelty; consume only via a future authorised integration. |
| Trigger evaluation and alert/action-protocol activation | Thresholds platform public product text | Do not rebuild a generic trigger-alert engine. |
| Public multi-hazard/seasonal/admin data | Thresholds API and tiles | Reuse as source of truth and demo evidence. |
| A public, complete workflow joining source freshness, assumptions, local impact/exposure, pre-agreed actions, owner readiness, finance readiness, and an immutable decision packet | **Publicly unverified** in inspected Husika/Thresholds surfaces | The best complementary wedge; phrase as a public-surface gap, not an assertion about private ICPAC systems. |
| A public Husika write API or integration contract | **Publicly unverified** | Build an adapter interface and export/handoff artifact; do not claim live Husika dispatch without approval/credentials. |

### The product hypothesis

When a climate signal appears, the hardest question for an AA coordinator is not "can I send an alert?" It is:

1. Which official issue and policy version are we acting on?
2. What does the signal imply for this exact place, population, and horizon?
3. Which actions were agreed in advance, are affordable/feasible within the lead time, and who owns each one?
4. Is there sufficient evidence to approve activation—or is data, acknowledgement, authority, or logistics missing?
5. Can we later prove why the decision was made and learn from it?

Husika can communicate the result; the Thresholds system can monitor/evaluate signal conditions. Linda Protocol makes the **decision path inspectable and operationally complete**.

## 7. What to build: Linda Protocol

### 7.1 Product scope

**User:** a county early-warning/DRM officer preparing an AA activation with an NGO partner.

**One complete workflow:** select an ICPAC-admin area and forecast/replay issue → inspect source/freshness and policy inputs → apply a versioned, deterministic action policy → see eligible pre-agreed action cards, owners, cost/readiness assumptions, and blockers → collect acknowledgements → named human approves or rejects → export an Activation Decision Packet and a Husika-compatible message handoff.

```text
ICPAC public forecast / replay fixture
             │  raw response + retrieval time + SHA-256
             ▼
      Source adapter + schema validation
             │
             ▼
  Deterministic policy evaluator ─────► policy version + calculations
             │                                      │
             ▼                                      ▼
  impact/exposure assumptions ───────────────► action eligibility
             │                                      │
             └──────────────┬───────────────────────┘
                            ▼
                    Activation workspace
             ┌──────────────┼────────────────┐
             ▼              ▼                ▼
        action cards   acknowledgements  decision packet
             │              │                │
             └──────► approved message handoff / future Husika adapter
```

### 7.2 Core screens and their testable value

| Screen | Judge-visible proof | Must be real, not decorative |
|---|---|---|
| **Signal Inbox** | A source record with issue date, validity/lead time, location ID, freshness, and raw-link/hash | Query/cache current API data and show replay fallback clearly. |
| **Why this action?** | A calculation trace: hazard probability, exposure/vulnerability input, policy thresholds, confidence/data completeness | Pure deterministic function with unit tests and a policy version. |
| **Action Cards** | Pre-agreed action, lead time, owner, eligibility, required evidence, unit cost/assumptions, non-negotiable blocker | Versioned YAML/JSON content. Do not invent official government SOPs; label demo cards as illustrative until validated. |
| **Readiness Board** | Named roles acknowledge, decline with structured blocker, or request clarification | Event log and state machine; an unacknowledged action stays visibly incomplete. |
| **Activation Decision Packet** | Exportable HTML/PDF/JSON evidence bundle with source provenance, calculation, assumptions, action state, approver, and timestamp | Generate from persisted decision record; no hidden prompt/black-box result. |
| **Communication Handoff** | A reviewed, localised message payload and recipient/target metadata queued for an authorised Husika integration | Export is real; “sent through Husika” is shown only if an authorised API is available. |

### 7.3 The decision policy: transparent by construction

Use a versioned `policy.yaml` rather than magic constants in code. **Reuse before calculating:** when an authorised ICPAC IBF/CRMA record supplies a posterior, CRMA state, impact tier, cost-loss ratio, `C/L`, or storyline, preserve it verbatim with source/version metadata. Do not reproduce the Bayesian-network or cost-loss model. A demo-only rule may combine a hazard value, local exposure/vulnerability score, operational readiness, and a cost-loss comparison only when every number is visibly labelled as a team-authored policy assumption:

```text
expected_avoidable_loss = P(hazard) × exposed_households × loss_per_household × action_effectiveness
net_expected_benefit    = expected_avoidable_loss − (unit_action_cost × eligible_households + fixed_cost)

recommendation =
  “consider activation” only when:
    source is fresh AND
    deterministic signal gate passes AND
    approved action has enough lead time AND
    data-completeness gate passes AND
    net_expected_benefit exceeds the locally configured margin
```

This is a **decision-support calculation**, not a claim that ICPAC, government, or a financing partner accepts the supplied values. Every input must show its source and be editable only by authorised policy roles. A named human makes the activation decision. This avoids both model risk and the unethical hackathon temptation to claim automatic relief-fund disbursement.

### 7.4 AI: useful, visible, constrained

| Assist | Allowed | Never allowed |
|---|---|---|
| Evidence Explainer | Turn structured facts/calculation into plain-language rationale; cite source IDs and report missing inputs | Change a source value, invent a probability, call a trigger, or conceal uncertainty. |
| Approved-Action Matcher | Retrieve only from the versioned action-card library and return structured candidates/reasons | Invent an action, cost, agency commitment, or financing agreement. |
| Feedback/Blocker Structurer | Classify free text into a controlled blocker taxonomy with human review | Treat unverified feedback as official data or use it as the sole activation trigger. |

All AI responses must validate against a strict JSON schema. The UI should visibly distinguish **official source**, **policy assumption**, **user-entered operational update**, and **AI explanation**. That information architecture is itself a strong trust/UX feature.

### 7.5 Explicit non-goals

- No autonomous finance release, beneficiary eligibility decision, emergency command, or automatic public alert.
- No replacement Husika app, Android/iOS build, Telegram bot, USSD shortcode, SMS gateway, or generic chatbot.
- No claim of a Husika write API without authorisation.
- No attempt to recalculate ICPAC's meteorology, train a climate model, or turn undocumented public endpoints into a promised production service.
- No broad “multi-agent platform” theatre: three narrow constrained assists are enough.

## 8. Technical architecture that will persuade developers

### 8.1 Build the smallest credible production-shaped system

Use a single deployable web product with explicit boundaries, rather than the current planned front-end, FastAPI, Telegram, SMS, USSD, PWA, APK, RAG, vector database, and PDF estate.

| Layer | Recommendation | Rationale |
|---|---|---|
| UI | Next.js/React/TypeScript + MapLibre (only for source context) | Fast, deployable, typed, and demonstrable. Use ICPAC vector tiles/client map; avoid duplicating GIS storage. |
| Decision service | FastAPI/Python + Pydantic | Natural fit for typed rules, PDF generation, source adapters, data fixtures, and transparent calculations. |
| Persistence | SQLite for a polished local/replay demo; PostgreSQL only if the team has it working early | An auditable append-only decision/event record matters more than premature PostGIS/pgvector. |
| Upstream adapter | HTTP client with schema validation, retry/backoff, TTL cache, raw immutable response store, and replay fixture | Public endpoints can drift. A healthy live API enriches the demo; it must never be a single point of failure. |
| Policies/actions | Versioned YAML/JSON files validated in CI | Makes every threshold/action/cost assumption reviewable and reproducible. |
| Packet | HTML-to-PDF plus signed/hashed JSON manifest | Gives a technical judge an artefact they can inspect rather than a dashboard screenshot. |
| Husika boundary | `ChannelHandoff` interface + export adapter | Honest integration architecture until ICPAC authorises credentials/API. |

### 8.2 Non-negotiable domain model

```text
SourceSnapshot      id, adapter, URL, retrieved_at, payload_hash, payload, freshness_status
PolicyVersion       id, hash, author, effective_from, rules
ActionCard          id, version, hazard, geography, lead_time, owner_role, prerequisites, costs
DecisionCase        id, area_id, source_snapshot_id, policy_version_id, state, created_at
EvidenceItem        decision_case_id, type, source_ref, confidence, reviewer_status
ReadinessTask       decision_case_id, action_card_id, owner, due_at, state, blocker_code
DecisionEvent       case_id, actor, action, timestamp, before_hash, after_hash, reason
ActivationPacket    case_id, manifest_hash, generated_at, approver, export_url
ChannelHandoff      case_id, target, payload_version, approval_state, exported_at
```

Case state machine:

```text
INGESTED → ASSESSED → NEEDS_EVIDENCE ──────────────┐
                 │                                  │
                 ▼                                  │
          READY_FOR_REVIEW → APPROVED → HANDED_OFF  │
                 │                  │               │
                 ▼                  ▼               │
             REJECTED          REVOKED ─────────────┘

Impossible transitions: an AI assist cannot enter APPROVED; a case with a
critical blocker cannot enter READY_FOR_REVIEW; a packet records its inputs'
hashes and cannot be silently overwritten.
```

### 8.3 Failure posture

| Failure | Required behaviour |
|---|---|
| ICPAC API timeout/429/schema change | Preserve last verified snapshot, label it stale, switch to replay only after explicit user confirmation, log the adapter error. |
| No valid live forecast crosses the demo policy | Do not manufacture a crisis. Show the current source as “no demo activation” and use a clearly labelled historical/replay case for the full workflow. |
| Missing exposure/cost/action-owner data | Block recommendation/approval; show a specific missing-data checklist. |
| LLM invalid JSON/refusal | Never fall back to prose parsing; mark assist unavailable and retain the deterministic workflow. |
| Two reviewers act concurrently | Optimistic version check; append an event, never overwrite a decision. |
| Husika integration unavailable | Export a reviewable handoff JSON/CSV/message preview; do not display “sent.” |

### 8.4 Tests a technical judge will respect

- Unit tests: policy boundary values; arithmetic; invalid/stale snapshots; impossible state transitions; packet manifest hash stability.
- Contract tests: recorded API fixtures for the datasets, forecast, admin-area, and tile metadata responses; fail clearly on schema drift.
- Integration test: source snapshot → decision case → action-card match → acknowledgement → approval → packet export.
- End-to-end demo test: live adapter or fixture fallback, rendering exact provenance and a completed approval path.
- Security tests: role separation; no direct object reference across cases; untrusted feedback escaped; no secrets in packet; LLM input/output schema checks.

## 9. Three product approaches considered

| Approach | Value | Duplication risk | Feasibility by 31 July | Verdict |
|---|---|---:|---:|---|
| Keep original **Linda Node**: new Telegram/SMS/USSD/PWA warning platform with RAG | Broad, understandable story | Very high | Low: many channel integrations, no existing code | Reject. It collides with Husika and ICPAC's stated Gemini direction. |
| Build a **generic climate chatbot / map** on ICPAC APIs | Easy demo | Very high | Medium | Reject. It will look like an attractive wrapper around work ICPAC already does. |
| **Linda Protocol**: trigger-to-action readiness, provenance, policy, tasks, packet, Husika handoff | Directly serves AA governance/activation gap | Low-to-medium; validate with judges as a complement | High if one workflow is polished | **Choose this.** It is technically deep, honest, and has a clear adoption story. |

## 10. Five-minute demo that tells the truth

| Time | Scene | Proof point |
|---:|---|---|
| 0:00–0:35 | Show the ICPAC Thresholds system and Husika, then say what they already solve | Respect for incumbent infrastructure; no duplicate-app pitch. |
| 0:35–1:10 | Open Linda Protocol's Signal Inbox for a real API snapshot | Exact endpoint, retrieved timestamp, hash, valid season/lead time, area ID. |
| 1:10–1:55 | Open “Why this action?” | Deterministic calculation trace and clearly marked policy assumptions. |
| 1:55–2:45 | Use the labelled replay case | A forecast signal + exposure/action policy produces specific eligible action cards, not generic AI prose. |
| 2:45–3:30 | Complete readiness tasks and show a blocker | Human accountability and a failed/blocked path; more credible than a flawless demo. |
| 3:30–4:20 | Human approval and Decision Packet export | Provenance, action owner, evidence inputs, and packet hash. |
| 4:20–4:45 | Show Husika-compatible handoff preview/export | Complementary integration, no fabricated send claim. |
| 4:45–5:00 | State limits and next integration ask | “We need ICPAC/National partners to validate policy values and authorise channel integration.” |

## 11. Delivery plan: nine days, one non-negotiable slice

| Day | Deliverable | Exit criterion |
|---:|---|---|
| 1 | Repo reset, domain schema, replay fixture, source adapter contract | A cached ICPAC response is rendered with time/hash and a fixture can replace it. |
| 2 | Policy engine and action-card schema | Boundary-value tests pass; calculations are rendered verbatim. |
| 3 | Decision Case UI and Signal Inbox | A selected area/issue creates a persisted case. |
| 4 | Readiness task state machine and role checks | Incomplete critical task blocks review; event log shows every mutation. |
| 5 | Packet generator | HTML/PDF + JSON manifest are generated from a completed case. |
| 6 | Constrained AI assists and Husika handoff export | Invalid model output cannot affect decision state. |
| 7 | Integration/E2E tests, seeded replay, deployment | A clean browser runs the full flow without manual database repair. |
| 8 | Demo recording, README, Devpost text, source acknowledgements | A colleague can reproduce the demo using documented commands. |
| 9 | Buffer and live-demo rehearsal | Record a backup video; rehearse failure-mode narration. |

If behind schedule, cut in this order: live map → LLM action matcher → live API (retain fixture + recorded raw source) → PDF styling. Do **not** cut policy trace, event log, replay fixture, state-machine block, or packet provenance; those are the product.

## 12. Submission narrative drafts

### Project overview (≤250 words)

Early-warning information is increasingly available across the Greater Horn of Africa, but a forecast does not by itself answer the operational question that follows: *which pre-agreed action should start now, who must own it, and is there enough evidence to approve it?* Existing systems such as ICPAC's Triggers & Thresholds platform and Husika are critical: they monitor risk and communicate trusted alerts across SMS, USSD, mobile, and web. Linda Protocol does not replace them.

Linda Protocol is an auditable activation-readiness workspace for county disaster officers and anticipatory-action partners. It ingests a versioned ICPAC forecast/trigger snapshot, records provenance and freshness, and applies a transparent local policy that combines the hazard signal with exposure, vulnerability, lead time, and pre-agreed action assumptions. The outcome is not an opaque AI decision or an automatic financial release. It is a reviewable decision case: eligible action cards, accountable owners, required evidence, readiness tasks, and blockers.

Named human approvers can approve, reject, or request more evidence. Every transition is logged; an Activation Decision Packet exports the source data, policy version, calculations, tasks, approvals, and a cryptographic manifest. A Husika-compatible handoff then prepares an approved message for authorised downstream communication.

By making the forecast-to-action chain inspectable, Linda Protocol helps partners act earlier with shared evidence while preserving human authority and existing ICPAC delivery systems.

### Solution details (≤250 words)

Linda Protocol is a Next.js/TypeScript and FastAPI/Python web application with a typed, versioned decision model. A resilient ICPAC adapter reads publicly available Thresholds & Triggers metadata, seasonal forecast, statistics, and administrative-area services. Each raw response is schema-validated, cached with retrieval time and SHA-256 hash, and shown in the UI. A labelled replay fixture makes the prototype reliable when a public upstream endpoint is unavailable or no live signal crosses the demo threshold.

The deterministic policy engine—not an LLM—evaluates source freshness, hazard threshold, exposure/vulnerability inputs, action lead time, readiness, and an optional transparent cost-loss comparison. It returns a calculation trace and never approves funds, chooses beneficiaries, or sends public alerts. Action cards are constrained to a reviewed library with owners, prerequisites, costs, and evidence requirements. A state machine prevents approval when critical tasks remain incomplete and records an append-only event trail.

AI is used narrowly: structured JSON explains the evidence, matches only approved action cards, and classifies operational blockers for human review. Every source, policy assumption, user input, and AI explanation is visibly separated. On approval, the system generates a PDF/JSON Activation Decision Packet with a hashed manifest and exports a Husika-ready communication handoff. This makes the decision path reproducible, governable, and ready for authorised channel integration.

## 13. Risks, questions to ask ICPAC, and non-negotiable honesty

### Questions for mentor/judge conversation

1. Which decision/action workflow is most painful today after a Thresholds trigger is evaluated: policy selection, inter-agency approval, logistics/owner acknowledgement, evidence packaging, or outcome learning?
2. Does an approved Husika integration/export API exist for partner projects? If not, what payload/content approval contract would be useful?
3. Which existing AA SOP/action-protocol artefacts may be used as a demo policy, and which must remain synthetic?
4. Which exposure/vulnerability sources are authoritative for a chosen county/hazard? Can any public source be cited in the prototype?
5. What is the acceptable human authority model for the demo: county officer, NGO programme manager, or a two-person approval?

### Claims to avoid

- “First/only last-mile early-warning app in IGAD.”
- “Husika lacks SMS/USSD/apps/feedback/approval/geo-targeting.”
- “ICPAC has no trigger automation” or “no action protocols.”
- “We integrate with Husika” unless an authorised integration is actually demonstrated.
- “Official ICPAC trigger/funding policy” for thresholds, costs, or actions created by the team.
- “AI decides/release funds/prevents disaster.”

### Recommended README corrections before any implementation

The README is a useful brainstorm but should not be used as the submission's factual foundation without these corrections. This report does **not** change it; these are recommended edits for the team to decide separately.

| README issue | Evidence-based correction |
|---|---|
| “Physical evaluation workshop at ICPAC, Ngong, Kenya” | Say “physical evaluation workshop; venue and demo format to be confirmed.” Devpost establishes the workshop, while [GHACOF74](https://www.icpac.net/events/ghacof74-harnessing-climate-services-for-early-action-and-resilience-in-the-greater-horn-of-africa-region-in-the-face-of-a-strong-el-ni%C3%B1o/) is in Kigali on 17–18 August 2026. |
| “Public GitHub repository” as an absolute requirement | Devpost says GitHub link “where applicable”; an organiser says a private repository is acceptable if organisers receive access. A public repo remains the lowest-friction choice. |
| “Missing last-mile delivery layer”; proposed Telegram/SMS/USSD/PWA/APK as differentiation | Remove it. Husika already provides SMS, USSD, Android, iOS, web, geo-targeting, approval, and feedback. |
| Two-way “Community Sentinel” crowdsourcing as novel | Recast as optional, consented, structured corroboration. ICPAC training material documents Husika SMS feedback/crowdsourcing already. |
| “Live operational ICPAC API” | State “public endpoint observed on 22 July 2026”; display issue/retrieval time and stale-data behaviour. Public access is not a published stability or SLA commitment. |
| A specific current severe-rainfall/trigger narrative | Cite a source and issue date, or label it a seeded replay scenario. Never imply a demo fixture represents a current activation. |
| “Official Husika module by 2027” | Recast as “adapter-ready pending ICPAC/Husika partnership, API contract, and authorisation.” |

### GitHub organisation inventory: all public repositories inspected

The [`icpac-igad` API inventory](https://api.github.com/orgs/icpac-igad/repos?type=all&per_page=100) returned 65 public, non-archived repositories. The detailed audit is in §4.4; this appendix records the complete scope so that no conclusion is based only on the most visible repositories. A repository's last push/README does not establish that a corresponding deployment is live, and public repository absence does not establish that a private component is absent.

| Portfolio | Repositories reviewed |
|---|---|
| Current IBF, climate-risk, forecast, decision support | [`arco-ibf`](https://github.com/icpac-igad/arco-ibf), [`bn-ibf`](https://github.com/icpac-igad/bn-ibf), [`code-for-earth`](https://github.com/icpac-igad/code-for-earth), [`crma`](https://github.com/icpac-igad/crma), [`DevOps-hazard-modeling`](https://github.com/icpac-igad/DevOps-hazard-modeling), [`e4drr`](https://github.com/icpac-igad/e4drr), [`ea-aifs`](https://github.com/icpac-igad/ea-aifs), [`ea-ibf-climada`](https://github.com/icpac-igad/ea-ibf-climada), [`ea-impact-events`](https://github.com/icpac-igad/ea-impact-events), [`fast-cgan`](https://github.com/icpac-igad/fast-cgan), [`flood_watch_system`](https://github.com/icpac-igad/flood_watch_system), [`geoserve`](https://github.com/icpac-igad/geoserve), [`grib-index-kerchunk`](https://github.com/icpac-igad/grib-index-kerchunk), [`ibf-thresholds-triggers`](https://github.com/icpac-igad/ibf-thresholds-triggers), [`prime-cgan`](https://github.com/icpac-igad/prime-cgan), [`rim2d-ibf`](https://github.com/icpac-igad/rim2d-ibf), [`SEWAA-forecasts`](https://github.com/icpac-igad/SEWAA-forecasts) (fork), [`sewaa-forecasts-package`](https://github.com/icpac-igad/sewaa-forecasts-package), [`stac-api`](https://github.com/icpac-igad/stac-api) |
| Hazards Watch, GIS, data preparation, visualisation | [`cGAN_tutorial`](https://github.com/icpac-igad/cGAN_tutorial) (fork), [`climatechange-api`](https://github.com/icpac-igad/climatechange-api), [`climsoft-db`](https://github.com/icpac-igad/climsoft-db), [`docker-ncwms`](https://github.com/icpac-igad/docker-ncwms), [`docker-pg_tileserv`](https://github.com/icpac-igad/docker-pg_tileserv), [`eadw-docs`](https://github.com/icpac-igad/eadw-docs), [`eahw-analysis-gee`](https://github.com/icpac-igad/eahw-analysis-gee), [`eahw-data-pre-processing`](https://github.com/icpac-igad/eahw-data-pre-processing), [`eahw-docs`](https://github.com/icpac-igad/eahw-docs), [`echarts-renderer`](https://github.com/icpac-igad/echarts-renderer), [`gee-tiles`](https://github.com/icpac-igad/gee-tiles) (fork), [`gsky`](https://github.com/icpac-igad/gsky) (fork), [`gsky-wps-api`](https://github.com/icpac-igad/gsky-wps-api), [`latest-imagery-api`](https://github.com/icpac-igad/latest-imagery-api), [`legend-image-generator`](https://github.com/icpac-igad/legend-image-generator), [`mapbox-windy`](https://github.com/icpac-igad/mapbox-windy), [`mukau-docs`](https://github.com/icpac-igad/mukau-docs), [`nc-to-gee`](https://github.com/icpac-igad/nc-to-gee), [`netcdf-vis`](https://github.com/icpac-igad/netcdf-vis) (fork), [`nrt-deploy`](https://github.com/icpac-igad/nrt-deploy), [`nrt-scripts`](https://github.com/icpac-igad/nrt-scripts), [`react-warming-stripes`](https://github.com/icpac-igad/react-warming-stripes), [`timeseries-mbgl-maps`](https://github.com/icpac-igad/timeseries-mbgl-maps), [`weatherlayers-gl`](https://github.com/icpac-igad/weatherlayers-gl) (fork), [`wms-animator`](https://github.com/icpac-igad/wms-animator) |
| Support, training, generic infrastructure and forks | [`adit_questionnaire`](https://github.com/icpac-igad/adit_questionnaire), [`cloud-compute-access`](https://github.com/icpac-igad/cloud-compute-access), [`django-bulma`](https://github.com/icpac-igad/django-bulma) (fork), [`docker-graylog`](https://github.com/icpac-igad/docker-graylog), [`downscaling-cgan`](https://github.com/icpac-igad/downscaling-cgan) (fork), [`ecflow`](https://github.com/icpac-igad/ecflow) (fork), [`gfs-public-downscaling-cgan`](https://github.com/icpac-igad/gfs-public-downscaling-cgan) (fork), [`ibf-workshop`](https://github.com/icpac-igad/ibf-workshop), [`igad-mesa`](https://github.com/icpac-igad/igad-mesa) (fork), [`layer-manager`](https://github.com/icpac-igad/layer-manager) (fork), [`python-cs-lesson`](https://github.com/icpac-igad/python-cs-lesson) (fork), [`python-workshop`](https://github.com/icpac-igad/python-workshop), [`SH`](https://github.com/icpac-igad/SH), [`Systems_documentation`](https://github.com/icpac-igad/Systems_documentation), [`TAMSAT-ALERT_API`](https://github.com/icpac-igad/TAMSAT-ALERT_API) (fork), [`terriajs`](https://github.com/icpac-igad/terriajs) (fork), [`trefoil`](https://github.com/icpac-igad/trefoil) (fork), [`vizzuality-components`](https://github.com/icpac-igad/vizzuality-components) (fork), [`wagtail-admin-sortable`](https://github.com/icpac-igad/wagtail-admin-sortable) (fork), [`wagtail-leaflet-widget`](https://github.com/icpac-igad/wagtail-leaflet-widget), [`wagtail-news-image`](https://github.com/icpac-igad/wagtail-news-image) (fork) |

## 14. Source ledger

### Primary competition sources

- [IGAD Hackathon Devpost overview](https://igad-husika-hackathon.devpost.com/)
- [Hackathon resources](https://igad-husika-hackathon.devpost.com/resources)
- [Hackathon rules](https://igad-husika-hackathon.devpost.com/rules)
- [Project gallery status](https://igad-husika-hackathon.devpost.com/project-gallery)
- [Devpost manager: overview/resources are the full problem statement](https://igad-husika-hackathon.devpost.com/forum_topics/44239-problem-statement-topic)
- [Devpost manager: private GitHub access option](https://igad-husika-hackathon.devpost.com/forum_topics/44160-submission)
- [Devpost eligibility clarification/forum conflict](https://igad-husika-hackathon.devpost.com/forum_topics/44177-indians-allowed)

### ICPAC and Husika sources

- [Husika public site](https://husika.icpac.net/)
- [How Husika Works](https://husika.icpac.net/how-husika-works)
- [Husika Android listing](https://play.google.com/store/apps/details?id=com.husika.app&hl=en)
- [Husika iOS listing](https://apps.apple.com/ke/app/husika/id6748664825)
- [ICPAC: Husika last-mile article](https://icpac.medium.com/husika-enabling-igad-member-states-reach-the-last-mile-with-actionable-early-warnings-11e8997a2ed4)
- [ICPAC: cloud modernisation and future Gemini/Husika direction](https://www.icpac.net/news/icpac-strengthens-climate-services-delivery-with-90-faster-insights-on-google-cloud/)
- [ICPAC training manual describing Husika MIMS](https://www.icpac.net/documents/1040/Final_Training_Manual_Booklet_copy.pdf)
- [Husika privacy policy](https://husika.icpac.net/privacy-policy)
- [WMO Early Warnings for All framework](https://public.wmo.int/activities/early-warnings-all/wmo-and-early-warnings-all-initiative)

### Data and policy sources

- [Thresholds & Triggers platform](https://eatriggersthresholds.icpac.net/)
- [Thresholds dataset registry](https://eatriggersthresholds.icpac.net/api/datasets/)
- [Thresholds indicators](https://eatriggersthresholds.icpac.net/api/datasets/indicators/)
- [Thresholds seasonal forecast catalogue](https://eatriggersthresholds.icpac.net/api/datasets/forecasts/available/?forecast_type=return_period)
- [Thresholds tile catalogue](https://eatriggersthresholds.icpac.net/tileserv/index.json)
- [IGAD Regional Roadmap for Anticipatory Action](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf)
- [Kenya Anticipatory Action Roadmap](https://www.icpac.net/documents/923/Kenya-Anticipatory-Action-Roadmap-2024-to-2029.pdf)
- [ICPAC / Action Against Hunger IMPAACT announcement](https://www.icpac.net/news/action-against-hunger-and-the-igad-climate-prediction-and-applications-centre-icpac-launch-landmark-echo-funded-initiative-to-build-anticipatory-action-systems-across-the-greater-horn-of-africa/)
- [ICPAC Drought Watch](https://droughtwatch.icpac.net/)
- [ICPAC Hazards Watch](https://eahazardswatch.icpac.net/)
- [Kenya NDMA drought information](https://ndma.go.ke/drought-information/)

### ICPAC public code and implementation sources

- [All public `icpac-igad` repositories — GitHub API snapshot](https://api.github.com/orgs/icpac-igad/repos?type=all&per_page=100)
- [`arco-ibf` CRMA web README](https://github.com/icpac-igad/arco-ibf/blob/cmra-web/README.md) and [scenario-chat implementation](https://github.com/icpac-igad/arco-ibf/blob/cmra-web/app/api/scenario-chat/route.ts)
- [`bn-ibf` flood technical description](https://github.com/icpac-igad/bn-ibf/blob/jua-bnet/flood_ibf/flood_bn_ibf_system_v20260412.md) and [explicit Layer-1-risk / Layer-2-action boundary](https://github.com/icpac-igad/bn-ibf/blob/9e080ee833413f7992124f6c3bc76eb2b3140f6f/flood_ibf/probabilistic_logic_v20260413.md)
- [`bn-ibf` cost-loss/CRMA evidence commit](https://github.com/icpac-igad/bn-ibf/commit/9e080ee833413f7992124f6c3bc76eb2b3140f6f), [soft evidence commit](https://github.com/icpac-igad/bn-ibf/commit/18ad13bfca10f8680e2bda4be067f5f2f7e9b43e), [dynamic-BN/storyline commit](https://github.com/icpac-igad/bn-ibf/commit/969aba494fc46dffbaf124d2eb003ef2ae60e763), and [exposure integration commit](https://github.com/icpac-igad/bn-ibf/commit/c4433304533666866caef60f086e34044e4163fb)
- [`flood_watch_system` operational architecture](https://github.com/icpac-igad/flood_watch_system/blob/main/README.md), [`geoserve`](https://github.com/icpac-igad/geoserve/blob/main/README.md), [`ea-impact-events`](https://github.com/icpac-igad/ea-impact-events/blob/main/README.md), and [`ibf-thresholds-triggers`](https://github.com/icpac-igad/ibf-thresholds-triggers/blob/kmj/README.md)

## 15. Bottom line

The fastest route to a weak entry is to implement the original README literally. It overbuilds channels that Husika already has and AI conversations ICPAC has publicly announced. The strongest route is a narrow, technically defensible system that makes ICPAC's existing data and Husika's existing reach **actionable in a governed way**.

Build **Linda Protocol**: source-provenance + deterministic policy + pre-agreed action cards + readiness/acknowledgement + human approval + immutable packet + honest Husika handoff. Make the panel feel that the team understood their stack deeply enough to extend it, not just imitate it.

---

# Part II — Independent second-pass verification and gap analysis

**Prepared:** 22 July 2026 (second research pass, independent of Part I). Method: four parallel investigations — a Devpost re-sweep, a live Husika/Thresholds platform audit (including previously unexamined API surfaces), a fresh `icpac-igad` GitHub audit with commit-level verification, and a global anticipatory-action tooling landscape review that Part I did not attempt. Evidence labels follow Part I's convention (Verified / Publicly unverified / Inference).

**Overall verdict on Part I:** the core strategic pivot — do not rebuild Husika's channels; build the governed decision-to-action layer — survives every check and is *strengthened* by new evidence. But Part I missed five materially important things: ICPAC's own public trigger-action API (the single best demo hook available), Husika's public OpenAPI contracts, the global prior art the judges may know (510/IFRC), a direct hackathon competitor already public on GitHub, and a set of borrowable standards (CAP 1.2, machine-readable EAP schemas, stop triggers) that convert "nice workflow app" into "standards-literate infrastructure." Several Part I claims also need correction.

## 16. Corrections to Part I

| Part I claim | Second-pass finding | Action |
|---|---|---|
| Eligibility "appears inconsistent about South Sudan; ask hackathon@icpac.net" | **Verified resolved.** Jason Kinyua (Manager) stated the full list in [the eligibility forum thread](https://igad-husika-hackathon.devpost.com/forum_topics/44177-indians-allowed): "Uganda, Ethiopia, Kenya, Somalia, Sudan, **South Sudan**, Eritrea, Djibouti, Tanzania, Burundi and Rwanda." | Drop the caveat. Note: an unanswered forum question about mixed-country teams (US+Kenya) remains open — only relevant if the team adds a non-eligible member. |
| "ICPAC's 23 June 2026 cloud-modernisation article says it plans Gemini conversational interfaces… with Husika" | **Could not re-verify.** The verifiable cloud story is the [Digicloud Africa case study (16 July 2026)](https://digicloud.africa/icpac-google-cloud-modernization/): GKE microservices, BigQuery, Cloud Run, 8h→30min processing, −40% cost — **no Gemini mention**. The Gemini/Husika chatbot plan may exist but is not confirmed on any surface checked today. | Keep the strategic conclusion (don't pitch a chatbot) — it stands on Husika + the `arco-ibf` scenario-chat alone — but do not cite the Gemini claim in the submission unless re-verified. |
| `flood_watch_system` described as inspectable operational stack | Nuance: since the 2026-05-13 rewrite the repo is **pure orchestration**; the four application repos it pins (`geomanager-web`, `geomanager`, `georeport`, `geomapviewer`) are **private (404)**. | Unchanged conclusion (don't rebuild it), but don't imply its app code is publicly auditable. |
| `bn-ibf` exposure integration presented as existing capability | Nuance: exposure code (WorldPop/INFORM/OSM) exists, but the flood README's limitations section says fusing it into the operational risk output "is a separate roadmap item." | The impact/evidence card seam is *more* open than Part I implied — still label any exposure joins as team-authored, not official. |
| "Physical evaluation workshop; venue to be confirmed" | GHACOF74 is **17–18 August 2026, Kigali, Rwanda**, themed "…in the Face of a Strong El Niño," and releases the OND 2026 outlook. Winners announced 25 August — i.e., top-10 shortlisting happens between 31 July and GHACOF74, and finalists likely present around it. | Correct as Part I recommended, and exploit the El Niño/OND framing (see §18.6). |
| "A public Husika write API: publicly unverified" | **Superseded — see §17.2.** Husika's microservices publish full OpenAPI specs; write endpoints exist and are OAuth2-gated. | Reframe from "unknown API" to "documented, auth-gated API we validate against but do not call." Much stronger. |

## 17. Critical discoveries Part I missed

### 17.1 ICPAC's trigger engine has a public action pipeline — and its only actions are email and dashboard-update

**Verified (22 July 2026).** The Thresholds & Triggers platform exposes, beyond the dataset APIs Part I found, a full **`/api/triggers/`** suite: [`/rules/`](https://eatriggersthresholds.icpac.net/api/triggers/rules/), [`/events/`](https://eatriggersthresholds.icpac.net/api/triggers/events/), [`/actions/`](https://eatriggersthresholds.icpac.net/api/triggers/actions/), [`/check-logs/`](https://eatriggersthresholds.icpac.net/api/triggers/check-logs/), with a browsable [Swagger UI](https://eatriggersthresholds.icpac.net/swagger/). Observed state:

- Three threshold **rules** (June 2026 test data, e.g. "Bungoma Triggers": `tmax ≥ 23.0°C` on `KEN.3_1`, fixed-value or return-period thresholds, severity, active flag, notification emails — including `crimson.sikolia@igad.int`, one of the judges).
- Three detected **events**; six **actions** — and the action-type vocabulary contains exactly two entries: **`email_alert`** and **`dashboard_update`**.
- 122 **check-logs** from a scheduled daily monitor running through 10 July 2026.

**Consequence — this is the demo's opening argument.** ICPAC's own operational pipeline detects a trigger, then sends an email and updates a dashboard. Everything after that — which pre-agreed action, who approves, what evidence, what happened — is undigitized. Linda Protocol is, concretely and demonstrably, *the missing third action type*. The Signal Inbox should ingest `/api/triggers/rules/` and `/api/triggers/events/` (alongside the forecast APIs), and the integration ask in the demo becomes precise: "register Linda as an action type on your existing rules." This is far sharper than Part I's generic "forecast snapshot" framing, and it speaks directly to the judge who authored the test rules.

### 17.2 Husika's backend contracts are public — the handoff can be schema-exact

**Verified.** Husika runs public-spec microservices: [`api.user.husika.icpac.net`](https://api.user.husika.icpac.net/openapi.json) (orgs, roles, OAuth2, GADM levels 0–3, FCM tokens), [`api.ingestor.husika.icpac.net`](https://api.ingestor.husika.icpac.net/openapi.json) (threats/forecasts/feeds/broadcasts, **`POST /v1/broadcast/fire`**, batch messages, retry), and [`api.feedback.husika.icpac.net`](https://api.feedback.husika.icpac.net/openapi.json). Live enums include **14 languages**, **17 event types** (flood, flash_flood, drought, …), content types (threat/forecast/feed/broadcast), threat levels (warning/watch/advisory/statement), and CAP-style **severity/urgency/certainty** fields. All write operations are OAuth2-gated.

**Consequence.** Part I's `ChannelHandoff` should not export a made-up payload: it should emit a message object that **validates against Husika's actual ingestor OpenAPI schema** (enum-correct event type, threat level, language, severity/urgency/certainty), with a CI test proving schema conformance. The demo line upgrades from "Husika-compatible export" to: "this payload validates against Husika's published API schema today; dispatch needs only credentials ICPAC controls." No access claim, maximal credibility — the Bunifu judges wrote or maintain that schema.

### 17.3 Husika's data model is CAP-shaped, but nobody in the stack emits CAP — open white space

**Verified.** Husika's fields mirror the [Common Alerting Protocol](https://cap-composer.readthedocs.io/) (severity/urgency/certainty/event), yet the strings "CAP"/"common alerting" appear **zero** times across all four OpenAPI specs, and no CAP/XML feed exists on any ICPAC surface checked. Meanwhile CAP is the centrepiece of WMO's Early Warnings for All: [20 African countries are implementing the WMO CAP Composer, alerts grew 22 → 456 between 2023 and 2024](https://wmo.int/media/magazine-article/common-alerting-protocol-milestones-of-early-warnings-all), and the [IFRC Alert Hub aggregates 227 national CAP feeds](https://www.alert-hub.org/alert-hubs). Kenya Met has a CAP alerts section; ICPAC publishing CAP is not publicly visible.

**Consequence.** Add a small, high-leverage feature: every approved activation also renders as a **valid CAP 1.2 alert** (plus an Atom feed endpoint). It is a few hundred lines against a stable XML schema, it makes Linda interoperable with the global alert-hub ecosystem rather than only Husika, and it aligns the pitch with EW4All language the ICPAC EWS program manager on the panel (Jully Ouma) will recognize instantly. This was entirely absent from Part I.

### 17.4 Competitor intelligence: the wedge is already being contested

**Verified.** GitHub already hosts visible hackathon activity:

- [`StephenJarso/kinga`](https://github.com/StephenJarso/kinga) (created 19 July 2026): "AI-powered anticipatory action trigger and activation engine for the IGAD region… turns pre-agreed thresholds into automatic, tracked action, delivered via a resilient mesh network." It includes a JSON trigger schema (SPI + IPC-phase conditions) and a problem statement citing IGAD's activation-counting gap. Its stack (Lovable-generated React front end, "automatic" activation, mesh-network claim) is shallower than Linda Protocol's, but the *category* — trigger-to-activation engine — will not be unique on judging day.
- [`mark124/husika-alert`](https://github.com/mark124/husika-alert) (17 July 2026): an ineligible US participant's MIT-licensed idea gift — named-disaster catalogue, human-in-the-loop approval, an AI "faithfulness gate." Worth skimming; it signals what ideas are already in the judges' air.
- Two other visible entries (conflict early signals; community health/livestock early warning).

**Consequence.** Differentiation cannot rest on the idea alone. It must rest on execution depth the category rivals won't have: real ingestion of ICPAC's trigger/forecast APIs with provenance, deterministic tested policy, the state machine and append-only audit, schema-exact Husika handoff, CAP export, and honest governance framing (no "automatic" activation — the panel's AA people know automaticity without governance is a bug, not a feature; kinga's "automatic, tracked action" is exactly the claim §7.3 warns against).

### 17.5 The IGAD evidence that makes the problem undeniable

**Verified.** IGAD/ICPAC published a [terms of reference (July 2025)](https://igad.int/wp-content/uploads/2025/07/Terms-of-Reference-Consulting-Services-to-Support-ICPAC-in-Undertaking-a-Regional-Mapping-and-Baseline-Survey-of-Anticipatory-Action-Initiatives-in-Eastern-Africa-Region.pdf) hiring a consultant for **six months** — under the WFP-financed SCALAA-GHA project — to manually map AA initiatives and count "the number of AA activations done during the 2020–2025 period," including existing "tools and systems like AA Plans and Protocols." Complementary: [OCHA's Eastern Africa AA activations report](https://www.unocha.org/publications/report/ethiopia/anticipatory-action-activations-eastern-africa-january-2024-december-2025-december-2025) (6M people, 10 countries, 2024–2025) is likewise a compiled PDF, and [KIPPRA documents that Kenya's Drought Contingency Fund often releases funds only after deterioration](https://kippra.or.ke/effectiveness-of-drought-response-interventions-in-arid-and-semi-arid-lands-in-kenya/).

**Consequence — the one-sentence problem statement:** *"IGAD currently has to hire a consultant for six months to count how many anticipatory activations even happened; Linda Protocol makes every activation a queryable, auditable record the moment it is approved."* This is regional, sourced, and unanswerable. Use it in the 250-word overview and at 0:00 of the video.

## 18. The global prior-art map Part I skipped — and what to borrow

### 18.1 Differentiation risks (judges may know these; have answers ready)

| Prior art | What it already does | Why Linda still stands |
|---|---|---|
| [Red Cross 510 IBF-system](https://github.com/rodekruis/IBF-system) (Apache-2.0; NestJS/Angular) | Trigger visualization, per-area early-action check-off, email/WhatsApp notification, a "Trigger Log" of past events; operational for Uganda floods (first EAP activation Nov 2023), drought portals in development for Ethiopia/Kenya/Uganda | Red Cross–internal tooling around IFRC EAPs; **no multi-party approval workflow, no signed/immutable evidence packet, no audit-grade decision record** (wiki documents roles, not approvals); not built on ICPAC's trigger/forecast APIs; not county-government-facing; no CAP out; no Husika handoff |
| [IFRC/510 "National Risk Watch"](https://510.global/2026/04/national-risk-watch-a-shared-platform-to-scale-anticipatory-action/) (announced Apr 2026) | Promises threshold management and "traceable, data-driven decision records" inside IFRC GO; Malawi pilot | Announced, not shipped regionally; IFRC-ecosystem-bound. Cite it as *validation* that decision records are the recognized gap |
| [IFRC GO digital EAP module + automated trigger-monitoring MVP](https://ifrcgoproject.medium.com/from-forecast-to-action-building-the-mvp-for-automated-eap-trigger-monitoring-655147cb7b2b) | GloFAS-based auto-monitoring → email to DREF team | The article itself notes no approval/audit workflow; email-only — same shape as ICPAC's own `email_alert` action (§17.1) |
| [WFP PRISM](https://github.com/WFP-VAM/prism-app) (MIT, Digital Public Good) | Hazard+vulnerability map dashboards with user-defined threshold alerts | Monitoring, not activation governance. Avoid demoing anything that reads as "map + threshold + alert" alone |
| [OCHA/CERF AA frameworks](https://www.unocha.org/anticipatory-action) | The canonical governance chain: pre-agreed trigger + plan + finance → ERC decision → counter-signed approval letters | The chain exists **on paper**. Position Linda as digitizing precisely this governance pattern, not inventing it |
| [Anticipation Hub trigger/early-action/evidence databases](https://www.anticipation-hub.org/experience/triggers/trigger-database/trigger-list/page-7) | Structured registry of trigger designs incl. stop mechanisms | Reference content, not workflow software; borrow its vocabulary (§18.2) |

The honest positioning sentence for judges: *"Globally, IFRC is building decision records into National Risk Watch and OCHA formalizes activation on paper; nobody has shipped an open, ICPAC-native activation desk for county and national actors in this region — that is the seam we fill, on your APIs."*

### 18.2 Borrowable standards and patterns (cheap to add, disproportionate credibility)

1. **Stop trigger as a first-class policy object.** The [trigger database](https://www.anticipation-hub.org/news/the-trigger-database-is-live) documents stop mechanisms as standard AA design; `policy.yaml` should carry `stop_trigger` and the state machine should include a revocation path driven by it. AA-literate judges will look for it.
2. **Ready–Set–Go double confirmation.** WFP Mozambique's published trigger design ([NHESS 2024](https://nhess.copernicus.org/articles/24/4661/2024/); hit rate 74%, false-alarm ratio 59%) — model policy stages `ready` (long-lead) → `set` → `go` (short-lead confirmation), and display hit-rate/FAR and an "acting in vain" note next to any trigger where skill data exists. One UI card, large trust dividend.
3. **EAP budget anatomy.** Real Kenya Red Cross EAPs split budgets into readiness/pre-positioning vs. trigger-released tranches ([drought EAP2022KE02: CHF 499,199 = 135,978 + 363,222](https://reliefweb.int/report/kenya/kenya-drought-early-action-protocol-summary-eap2022ke02); [riverine floods EAP2021KE01](https://reliefweb.int/report/kenya/kenya-riverine-floods-early-action-protocol-summary-eap2021ke01)). Action cards should carry this two-tranche structure with those documents citable as the pattern source.
4. **NDMA vocabulary for the Kenya demo.** County officers think in NDMA phases (Normal/Alert/Alarm/Emergency/Recovery) and [VCI3M < 35 as the assessment/contingency-fund trigger](https://ndma.go.ke/drought-information/). Displaying ICPAC signal *and* NDMA phase semantics side-by-side makes the tool read as native to its user.
5. **Machine-readable action-protocol schema, Montandon-aligned.** IFRC's [Montandon Global Crisis Data Bank](https://go.ifrc.org/montandon-landing) and the [Monty STAC extension](http://ifrcgo.org/monty-stac-extension/) are the emerging standard for machine-readable EAP definitions (hazard, return period, probability, lead time, areas, actions). Publishing Linda's `ActionCard`/policy JSON Schema and citing that direction signals standards literacy.
6. **CAP 1.2 emission** (§17.3) — the interoperability capstone.
7. **Kenya's legal moment.** The [National Disaster Risk Management Act (No. 16 of 2026, commenced 2 June 2026)](https://new.kenyalaw.org/akn/ke/act/2026/16/eng@2026-06-02), the National DRM Strategy 2025–2030, and the announced 5% of DRM budget for EWS give the impact story a statutory hook Part I lacked: counties now have a legal DRM mandate but no activation software. One line in the overview; large "Problem Value" payoff.

### 18.3 New facts that sharpen the demo scenario

- **El Niño + OND 2026 is the season the judges will be living in.** GHACOF74 (where finalists appear) is themed on a strong El Niño and releases the OND 2026 outlook; the Thresholds API already serves the **OND 2026 return-period forecast (issued July, lead 3 months)**. The primary live demo case should therefore be an OND 2026 case built on that exact issue — the same data on screen in Kigali — with the historical replay fixture as the completed-workflow backup. Part I's "drought or flood, generic adapter" stands, but this issue is the one to feature.
- **Husika adoption is early-stage** (Play Store 100+ downloads; iOS listing with zero ratings as of today). Never say this to disparage — the correct use is the partnership frame: Linda increases the value of every Husika alert by attaching accountable decisions to it, and arrives while the ecosystem is still forming.
- **Voice is taken.** Husika's TTS layer is in active development this month by Speedykom under GIZ funding ([husika-tts-icpac](https://github.com/Speedykom/husika-tts-icpac), pushed 20 July 2026; Swahili/Oromo/Amharic/Somali + Karamoja-cluster languages). Reinforces Part I: no voice/TTS features in scope, even on the roadmap slide.
- **ICPAC's current build direction** (from fresh commits): ARCO forecast stores (Icechunk/Zarr on source.coop), the CRMA scenario app with an LLM chat merged 12 June, AIFS GPU ensembles, Overture-Maps exposure, ecFlow orchestration, and a new `geoserve` STAC/tiles bundle gaining an `eafw` branch. Nothing ICPAC is publicly building overlaps Linda's decision layer — while `bn-ibf`'s own decision-mapping doc says the Layer-2 rule must live "OUTSIDE the BN… clear, auditable." ICPAC's documentation is, in effect, requesting Linda Protocol.
- **Devpost hygiene:** updates page empty, gallery unpublished, no separate problem statement exists (organizer-confirmed: overview + resources *are* the brief), "web link **or** APK" explicitly accepted, and "Innovation & AI Creativity (30%)" is scored as *effective application of AI* — so the three constrained assists must be visibly exercised in the video, including one on-camera failure/refusal (invalid JSON → assist unavailable, workflow continues).

## 19. Spec deltas to Part I (what actually changes in the build)

1. **Adapter scope** (§4.2/§8.1): add `/api/triggers/rules|events|actions|check-logs` to the source adapter. Signal Inbox shows ICPAC's *own* rules and detected events with provenance, not only forecast issues. Contract-test fixtures for these four endpoints.
2. **ChannelHandoff** (§7.2/§8.1): generate payloads validated in CI against Husika's published ingestor OpenAPI schema (enums for event type, threat level, language, severity/urgency/certainty). Add a second exporter: **CAP 1.2 XML + Atom feed** per approved activation.
3. **policy.yaml** (§7.3): add `stop_trigger`, `stages: [ready, set, go]`, optional `skill: {hit_rate, far, source}` display fields, and two-tranche cost structure on action cards (`readiness_cost`, `activation_cost`).
4. **State machine** (§8.2): `REVOKED` transitions must be reachable from a stop-trigger evaluation, not only manual revocation; event log records which stop condition fired.
5. **Demo script** (§10): open with the §17.1 line — show ICPAC's live `/api/triggers/actions/` returning `email_alert` / `dashboard_update`, then: "here is action type three." Feature the OND 2026 El Niño issue as the live case. Close impact with the §17.5 consultancy sentence and the DRM Act hook.
6. **Submission text** (§12): weave in (a) the six-month activation-counting consultancy, (b) schema-validated Husika handoff + CAP export, (c) Kenya DRM Act 2026 — all within the existing 250-word budgets by trimming generic sentences.
7. **Claims discipline additions** (§13): do not claim "first activation platform" (510 IBF and National Risk Watch exist — cite them as validation); do not describe activation as "automatic" (kinga's mistake); do not cite the Gemini plan unless re-verified; do not present the Bungoma test rules as operational policy — they are visibly test data.

## 20. Part II source ledger (new sources only)

- Thresholds trigger pipeline: [rules](https://eatriggersthresholds.icpac.net/api/triggers/rules/) · [events](https://eatriggersthresholds.icpac.net/api/triggers/events/) · [actions](https://eatriggersthresholds.icpac.net/api/triggers/actions/) · [check-logs](https://eatriggersthresholds.icpac.net/api/triggers/check-logs/) · [Swagger](https://eatriggersthresholds.icpac.net/swagger/)
- Husika OpenAPI: [user](https://api.user.husika.icpac.net/openapi.json) · [ingestor](https://api.ingestor.husika.icpac.net/openapi.json) · [feedback](https://api.feedback.husika.icpac.net/openapi.json)
- [IGAD/ICPAC AA mapping & baseline survey ToR (SCALAA-GHA, July 2025)](https://igad.int/wp-content/uploads/2025/07/Terms-of-Reference-Consulting-Services-to-Support-ICPAC-in-Undertaking-a-Regional-Mapping-and-Baseline-Survey-of-Anticipatory-Action-Initiatives-in-Eastern-Africa-Region.pdf) · [announcement](https://igad.int/job/consulting-services-to-support-icpac-in-undertaking-a-regional-mapping-and-baseline-survey-of-anticipatory-action-initiatives-in-eastern-africa-region/)
- [OCHA Eastern Africa AA activations 2024–2025](https://www.unocha.org/publications/report/ethiopia/anticipatory-action-activations-eastern-africa-january-2024-december-2025-december-2025) · [KIPPRA on DCF release delays](https://kippra.or.ke/effectiveness-of-drought-response-interventions-in-arid-and-semi-arid-lands-in-kenya/)
- Prior art: [510 IBF-system](https://github.com/rodekruis/IBF-system) ([wiki/Features](https://github.com/rodekruis/IBF-system/wiki/Features)) · [National Risk Watch](https://510.global/2026/04/national-risk-watch-a-shared-platform-to-scale-anticipatory-action/) · [IFRC GO EAP trigger-monitoring MVP](https://ifrcgoproject.medium.com/from-forecast-to-action-building-the-mvp-for-automated-eap-trigger-monitoring-655147cb7b2b) · [WFP PRISM](https://github.com/WFP-VAM/prism-app) · [OCHA AA](https://www.unocha.org/anticipatory-action) · [Start Network DRF](https://startnetwork.org/funds/disaster-risk-financing)
- Standards: [WMO CAP Composer](https://cap-composer.readthedocs.io/) · [WMO CAP milestones in Africa](https://wmo.int/media/magazine-article/common-alerting-protocol-milestones-of-early-warnings-all) · [IFRC Alert Hub](https://www.alert-hub.org/alert-hubs) · [Montandon](https://go.ifrc.org/montandon-landing) · [Monty STAC extension](http://ifrcgo.org/monty-stac-extension/)
- Trigger design & finance patterns: [Ready–Set–Go verification, NHESS 2024](https://nhess.copernicus.org/articles/24/4661/2024/) · [Kenya drought EAP2022KE02](https://reliefweb.int/report/kenya/kenya-drought-early-action-protocol-summary-eap2022ke02) · [Kenya floods EAP2021KE01](https://reliefweb.int/report/kenya/kenya-riverine-floods-early-action-protocol-summary-eap2021ke01) · [Anticipation Hub trigger database](https://www.anticipation-hub.org/experience/triggers/trigger-database/trigger-list/page-7) · [NDMA drought information](https://ndma.go.ke/drought-information/)
- Kenya policy: [DRM Act No. 16 of 2026](https://new.kenyalaw.org/akn/ke/act/2026/16/eng@2026-06-02) · [National DRM Strategy 2025–2030](https://ndoc.go.ke/kenya-launches-national-disaster-risk-management-strategy-2025-2030-strengthen-disaster-risk)
- Competitors & ecosystem: [kinga](https://github.com/StephenJarso/kinga) · [husika-alert](https://github.com/mark124/husika-alert) · [Speedykom husika-tts-icpac](https://github.com/Speedykom/husika-tts-icpac) · [Digicloud ICPAC modernization (16 July 2026)](https://digicloud.africa/icpac-google-cloud-modernization/) · [Eligibility forum answer](https://igad-husika-hackathon.devpost.com/forum_topics/44177-indians-allowed)

## 21. Part II bottom line

Part I's pivot is right; this pass makes it executable and defensible. The three moves that most increase win probability, in order:

1. **Anchor the demo on ICPAC's own `/api/triggers/` pipeline** — "your trigger engine's actions today are email and dashboard-update; we built the third action type" — and feature the live OND 2026 El Niño forecast issue the judges will present at GHACOF74.
2. **Make both handoffs schema-real:** a payload that validates against Husika's published OpenAPI enums, plus a CAP 1.2 export — turning "integration story" into demonstrable, testable artifacts against systems the judges themselves build.
3. **Own the evidence and the prior art before the judges raise them:** open with the six-month IGAD activation-counting consultancy and the Kenya DRM Act 2026 as the problem's proof; cite 510/IFRC National Risk Watch as validation of the gap while showing exactly what Linda ships that they don't — an open, ICPAC-native, multi-party-approved, immutable activation record.
