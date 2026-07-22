# Linda Protocol — TL;DR

> **⚠️ Direction update (22 July 2026):** the project has pivoted from "Linda Node" (below) to **Linda Protocol**. Build spec: [`what-to-build.md`](what-to-build.md) · evidence base: [`research.md`](research.md). The rest of this README describes the old concept and is pending rewrite.

**The problem:** Forecasts and alerts exist across the Greater Horn of Africa, but there is no digital system for what happens *after* a trigger fires — deciding which pre-agreed action to start, who approves it, and proving why — so activations are slow, undocumented, and IGAD literally hired a consultant for six months just to count them.

**What's been done:** ICPAC already owns the science and the delivery — Thresholds & Triggers monitors indicators and fires triggers (but its only actions are an email and a dashboard update), and Husika delivers alerts via SMS/USSD/apps/web — so warning generation and last-mile communication are solved, while the decision layer between them is not.

**Our solution (Linda Protocol):** An auditable activation workspace that ingests ICPAC's live trigger and forecast APIs with full provenance, runs a transparent deterministic policy (Ready–Set–Go stages, stop-triggers, cost-loss trace), walks pre-agreed action cards through a readiness board and three-role co-signing (EWS specialist, county DRM officer, NGO finance lead), and outputs an immutable signed decision packet plus CAP 1.2 alerts and a Husika-schema-validated handoff.

**Our unique edge:** We are demonstrably the "missing third action type" on ICPAC's own live pipeline — built on their real APIs, validating against Husika's published schema, exposing our own consumable API back to them, with AI constrained to explaining evidence rather than making decisions — so the judges (mostly ICPAC and Husika's own developers) see their stack extended with the governance layer their own docs admit is missing, not duplicated.

---

<div align="center">

# Linda Node: The Last-Mile Anticipatory Action Engine

**"Linda" means "protect" in Swahili. A Node is a point of connection between the community and ICPAC's data.**

An autonomous, multi-agent AI platform connecting ICPAC's ECMWF SEAS51 threshold triggers directly to localized anticipatory action and anticipatory disaster risk financing via Telegram and SMS in the Greater Horn of Africa.

*Built for the [IGAD Hackathon 2026: Smarter Early Warning, Stronger Communities](https://igad-husika-hackathon.devpost.com/)*

**This README is the single source of truth for this project.** It is written to fully brief any human developer **or** AI coding agent: what to build, how to build it, why it matters, and how it wins this specific hackathon.

</div>

---

## Table of Contents

1. [The Hackathon: Everything You Need to Know](#1-the-hackathon-everything-you-need-to-know)
2. [The Problem](#2-the-problem)
3. [The Solution: Linda Node](#3-the-solution-linda-node)
4. [Core Features & Innovations](#4-core-features--innovations)
5. [System Architecture](#5-system-architecture)
6. [ICPAC Data Infrastructure: What We Integrate With](#6-icpac-data-infrastructure-what-we-integrate-with)
7. [Implementation Guide (For Developers & AI Agents)](#7-implementation-guide-for-developers--ai-agents)
   - [7.1 Repository Layout](#71-repository-layout)
   - [7.2 Environment & Setup](#72-environment--setup)
   - [7.3 Database Schema](#73-database-schema)
   - [7.4 Data Ingestion Pipeline](#74-data-ingestion-pipeline)
   - [7.5 The Multi-Agent System](#75-the-multi-agent-system)
   - [7.6 Telegram Bot: Commands & Conversation Flows](#76-telegram-bot-commands--conversation-flows)
   - [7.7 Backend API Endpoints](#77-backend-api-endpoints)
   - [7.8 The Command Center Dashboard & Mini App](#78-the-command-center-dashboard--mini-app)
   - [7.9 Proof of Risk Dossier Generation](#79-proof-of-risk-dossier-generation)
   - [7.10 SMS & USSD Channel (Africa's Talking)](#710-sms--ussd-channel-africas-talking)
   - [7.11 PWA & Android APK Packaging (Offline Functionality)](#711-pwa--android-apk-packaging-offline-functionality)
   - [7.12 Deployment](#712-deployment)
8. [System Resiliency & Security Safeguards](#8-system-resiliency--security-safeguards)
9. [Application Walkthrough (User Journeys)](#9-application-walkthrough-user-journeys)
10. [Development Status, Build Plan & Milestones](#10-development-status-build-plan--milestones)
11. [Impact: Who Benefits and How We Measure It](#11-impact-who-benefits-and-how-we-measure-it)
12. [Alignment with Judging Criteria](#12-alignment-with-judging-criteria)
13. [Demo Video Plan & Submission Checklist](#13-demo-video-plan--submission-checklist)
14. [Future Roadmap (Post-Hackathon)](#14-future-roadmap-post-hackathon)
15. [Complete Resources, Sources & References](#15-complete-resources-sources--references)

---

## 1. The Hackathon: Everything You Need to Know

This project is a submission to the **IGAD Hackathon 2026: "Smarter Early Warning, Stronger Communities"**, organized by the [IGAD Climate Prediction and Applications Centre (ICPAC)](https://www.icpac.net/) — the WMO-mandated Regional Climate Centre serving 11 countries of the Greater Horn of Africa — and hosted on [Devpost](https://igad-husika-hackathon.devpost.com/).

**The challenge:** reimagine how early warning information is *generated, communicated, understood, and converted into timely action* across the IGAD region — for climate extremes, disasters, food insecurity, health emergencies, and humanitarian crises. Suggested solution spaces: mobile applications, geospatial technologies, data analytics, communication platforms, artificial intelligence, and community engagement tools.

### Key facts

| Detail | Value |
|---|---|
| **Submissions open** | June 22, 2026, 3:15pm EAT |
| **Submission deadline** | **July 31, 2026, 5:00pm EAT** |
| **Winners announced** | August 25, 2026, 11:00am EAT |
| **Prize pool** | $10,000+ cash plus sponsorships |
| **1st place** | $4,000 + GHACOF74 sponsorship + workshop |
| **2nd place** | $2,500 + GHACOF74 sponsorship + workshop |
| **3rd place** | $1,500 + GHACOF74 sponsorship + workshop |
| **4th–5th place** | $1,000 each + GHACOF74 sponsorship + workshop |
| **6th–10th place** | Workshop sponsorship |
| **Finals** | **Top 10 solutions advance to a physical evaluation workshop at ICPAC, Ngong, Kenya** — expect a live, in-person demo |
| **Team size** | Max 5 members |
| **Organizer contact** | hackathon@icpac.net |

### Judging criteria (weighted)

| Criterion | Weight | What judges look for |
|---|---|---|
| **Technical Depth & Engineering** | 30% | Implementation quality, architecture, functionality — *of working software, not slideware* |
| **Innovation & AI Creativity** | 30% | Originality, application of emerging technology |
| **Problem Value & Impact** | 25% | Meaningful challenge, measurable impact |
| **Presentation & Documentation** | 15% | Clarity, demonstration, communication |

The [rules page](https://igad-husika-hackathon.devpost.com/rules) additionally names **user experience** and **scalability** as assessed dimensions. Participants retain IP ownership; open-source tools must be properly acknowledged (this README's [Section 15](#15-complete-resources-sources--references) does exactly that).

### The judges — and why it shapes our strategy

1. **Mubarak Mabuya** — Coordinator, IGAD IDDRISI (disaster resilience policy)
2. **Jully Ouma** — Program Manager, Early Warning Systems, ICPAC
3. **Jason Kinyua** — Lead Developer, ICPAC
4. **Keith Korir** — Lead Developer, Bunifu Technologies
5. **Unika Mureithi** — Developer, Bunifu Technologies
6. **Mohammed Ali** — Developer, ICPAC
7. **Crimson Sikolia** — GIS Developer, ICPAC

**Strategic implication:** four of seven judges are ICPAC's own engineering/EWS staff — the people who *built* the data platforms we integrate with. This panel will (a) instantly detect inflated or fabricated technical claims, and (b) strongly reward genuine, correct integration with ICPAC's real open-source pipeline and platforms. Therefore Linda Node's strategy is **deep, verifiably-correct integration with ICPAC's published tooling** ([Section 6](#6-icpac-data-infrastructure-what-we-integrate-with)) and **complete honesty about build status** ([Section 10](#10-development-status-build-plan--milestones)).

### Required submission package

1. **Project Overview** (max 250 words) — [Section 2](#2-the-problem) below is written to spec
2. **Solution Details** (max 250 words) — [Section 3](#3-the-solution-linda-node) below is written to spec
3. **Working prototype** — web link or APK
4. **Demo video** — maximum 5 minutes ([our script: Section 13](#13-demo-video-plan--submission-checklist))
5. **Technology stack + public GitHub repository** — this repo

---

## 2. The Problem

### Project Overview (Max 250 words — submission-ready)

While ICPAC's Multi-Hazard Triggers and Thresholds System generates world-class predictive data, early warnings often fail at the **"last mile."** A pastoralist cannot easily interpret a Standardized Precipitation Index (SPI-3) map, nor do they benefit from generalized hazard alerts. The core problem is a **translation gap** between scientific hazard forecasting, localized impact-based action, and the financial means to execute that action.

**Linda Node** is an autonomous Anticipatory Action Engine designed to bridge this gap. Instead of a basic chatbot, Linda Node operates as a multi-agent AI architecture sitting directly on top of ICPAC's open-source [ibf-thresholds-triggers](https://github.com/icpac-igad/ibf-thresholds-triggers) pipeline. For vulnerable communities, it acts as a multilingual conversational agent deployed via a Telegram Bot & Mini App (with an SMS pathway on the roadmap). It translates complex ensemble forecast probabilities into personalized, actionable advice based on exact GPS coordinates, while allowing locals to report indigenous knowledge back to the system. For decision-makers and NGOs, Linda Node aggregates these crowdsourced reports, overlays them onto ICPAC hazard maps, and generates verifiable **"Proof of Risk" dossiers** — evidence packages that support the release of pre-arranged Anticipatory Disaster Risk Financing *before* the disaster strikes, in line with the [IGAD Regional Roadmap for Anticipatory Action](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf). This shifts the paradigm from reactive monitoring to proactive, funded resilience.

### The evidence for the gap

- **Early warnings exist; early action lags.** ICPAC operates [Hazard Watch](https://hazardwatch.icpac.net/), [Drought Watch](https://droughtwatch.icpac.net/), and the [Thresholds & Triggers Watch](https://eatriggersthresholds.icpac.net/) — but these are expert-facing GIS platforms. The farmer-facing delivery layer is precisely what ICPAC's [Husika platform](https://husika.icpac.net/) initiative exists to solve, and what this hackathon asks for.
- **Anticipatory action is the region's stated priority.** The [IGAD Regional Roadmap for Anticipatory Action](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf) commits the region to institutionalizing trigger-based pre-emptive financing. The ECHO-funded [IMPAACT initiative](https://www.actionagainsthunger.org/press-releases/action-against-hunger-and-the-igad-climate-prediction-and-applications-centre-icpac-launch-landmark-echo-funded-initiative-to-build-anticipatory-action-systems-across-the-greater-horn-of-africa/) (Action Against Hunger × ICPAC, launched July 2026) targets 243,801 people in Ethiopia, Somalia, and Djibouti with exactly this model.
- **Money is the missing link.** Research on forecast-based financing (e.g. [Mozambique drought FbF study, ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2405880723000055)) shows warnings without pre-arranged finance rarely change household behavior — you cannot sell livestock early, buy fodder, or reinforce a home with information alone.

---

## 3. The Solution: Linda Node

### Solution Details (Max 250 words — submission-ready)

Linda Node runs on a scalable, cloud-native architecture: a **Next.js / React / TypeScript** frontend delivered three ways — **web dashboard, installable offline-capable PWA, and Android APK** (via Capacitor) — alongside a highly concurrent **Python (FastAPI)** backend, with **Supabase (PostgreSQL + PostGIS)** handling state and geospatial indexing. The system consumes ICPAC's live Thresholds & Triggers API and is designed for interoperability with ICPAC's [Husika](https://husika.icpac.net/) platform.

The core innovation is a **Proactive Multi-Agent AI System** built on a current-generation frontier LLM (Google Gemini 2.x):

- **The Predictive Monitor Agent** ingests trigger outputs from ICPAC's threshold pipeline (SEAS51 ensemble forecasts and CHIRPS observations processed to SPI, with quantile-based threshold exceedance probabilities). When a forecast probability exceeds a predefined trigger, it flags the geospatial sub-county.
- **The RAG Context Agent** retrieves historical, agricultural, and indigenous context for the flagged region using Retrieval-Augmented Generation over ICPAC bulletins and community reports.
- **The Action Router Agent** synthesizes localized impact warnings and dispatches them per user's channel: rich alerts and an interactive map **Telegram Mini App**, plus **SMS broadcasts and an interactive USSD menu via Africa's Talking gateways** — so feature phones and data-dark areas receive the same warnings.

In parallel, the **Anticipatory Financing Module** activates when severe thresholds are met, generating a "Proof of Risk" PDF dossier — a standardized evidence package combining ICPAC trigger data, community consensus, and AI analysis. Local cooperatives and NGOs use this dossier to support the release of pre-arranged micro-loans or relief funds **days before** a climate shock occurs — with humans, not AI, making the final authorization.

---

## 4. Core Features & Innovations

### 4.1 Proactive Multi-Agent Architecture
Linda Node abandons the traditional "wait-for-a-prompt" chatbot model. It operates **asynchronously**: actively monitoring ICPAC data streams and pushing alerts out *before* the community asks, using three distinct LLM-powered agents to monitor, contextualize, and communicate risk dynamically based on the user's specific livelihood profile (e.g., maize farmer vs. pastoralist vs. county official). Full agent specification in [Section 7.5](#75-the-multi-agent-system).

### 4.2 True Multi-Channel Delivery: Telegram + SMS + USSD + Web/PWA/APK
Linda Node meets every user on the device they actually own:

- **Telegram Bot & Mini App** ([Bot API](https://core.telegram.org/bots/api) / [Mini Apps](https://core.telegram.org/bots/webapps)) — the rich-media channel: inline keyboards, photos, and the Next.js dashboard opening **directly inside the chat client**. Officials receive the "Proof of Risk" alert in chat, tap a button, and view live ICPAC overlays without leaving the app.
- **SMS via [Africa's Talking](https://africastalking.com/sms)** — outbound alert broadcasts and inbound keyword reporting (`REPORT pasture failing`) for any GSM phone, no data required.
- **USSD via [Africa's Talking](https://africastalking.com/ussd)** — an interactive `*384#`-style session menu (check my area's outlook / register / report conditions / change language) that works on **feature phones with zero internet** — the reality for a large share of pastoralist households.
- **Web dashboard, installable PWA, and Android APK** (same Next.js codebase via [Capacitor](https://capacitorjs.com/)) — the PWA/APK cache the latest trigger states and advisories with a service worker, so previously synced warnings remain **readable fully offline** in the field.

One backend, one alert pipeline, four delivery surfaces — coverage from smartphone to feature phone to no-signal.

### 4.3 Native Integration with ICPAC's Thresholds & Triggers Pipeline
Unlike generic weather apps relying on commercial APIs, Linda Node's backend consumes the outputs of ICPAC's own open-source drought trigger pipeline — the exact scripts, notebooks, and data formats are documented in [Section 6](#6-icpac-data-infrastructure-what-we-integrate-with). Linda Node is the missing **last-mile delivery layer** for ICPAC's existing geospatial data infrastructure.

### 4.4 The Anticipatory Financing Module ("Proof of Risk")
Early warnings are useless if communities lack the capital to act (buying fodder, drought-tolerant seed, sandbags; destocking early at fair prices). When threshold triggers are met, Linda Node generates a standardized PDF dossier documenting the imminent hazard for a specific GPS polygon — combining official trigger data, community report consensus, and AI-generated analysis. This serves as verified supporting documentation for pre-arranged humanitarian cash transfers or micro-loans under existing anticipatory action financing frameworks (see the [Anticipation Hub](https://www.anticipation-hub.org/) and [OCHA anticipatory action](https://www.unocha.org/anticipatory-action) models). **The dossier informs human decision-makers; it does not autonomously release funds.** Spec in [Section 7.9](#79-proof-of-risk-dossier-generation).

### 4.5 Epistemic Inclusion (Two-Way Crowdsourcing)
Communities are active data nodes, not passive recipients. Users send unstructured texts and photos via Telegram (e.g., *"The river is turning brown"*, *"Grass in our grazing area is finished"*). The LLM processes this local knowledge, tags it with coordinates, classifies it against a hazard taxonomy, and plots it as a live **"Community Sentinel" layer** alongside official [ICPAC Drought Watch](https://droughtwatch.icpac.net/) indicators — integrating indigenous knowledge with formal climate science, and feeding the consensus check that guards the financing module.

---

## 5. System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│  ICPAC DATA LAYER (upstream, open source)                              │
│                                                                        │
│  ECMWF SEAS51 seasonal forecasts        CHIRPS rainfall observations   │
│  (via Copernicus CDS)                   (via UCSB Climate Hazards Ctr) │
│          │                                        │                    │
│          ▼                                        ▼                    │
│  icpac-igad/ibf-thresholds-triggers pipeline:                          │
│  SPI computation → quantile thresholds → exceedance probabilities     │
│  per admin unit  (NetCDF / Zarr / CSV outputs)                         │
└──────────────────────────────┬─────────────────────────────────────────┘
                               │  ingestion worker (scheduled)
                               ▼
┌────────────────────────────────────────────────────────────────────────┐
│  LINDA NODE BACKEND — Python 3.11 / FastAPI                            │
│                                                                        │
│  /ingest worker ──► PostGIS (trigger_states, admin_units)              │
│                                                                        │
│  ┌──────────────────── Multi-Agent System (Gemini 2.x) ─────────────┐  │
│  │ 1. Predictive Monitor Agent — evaluates trigger exceedances      │  │
│  │ 2. RAG Context Agent       — regional/agri/indigenous context    │  │
│  │ 3. Action Router Agent     — drafts & routes localized alerts    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  Financing Module ──► Proof of Risk PDF dossiers (human-authorized)    │
│  Storage: Supabase (PostgreSQL + PostGIS)  ·  pgvector for RAG         │
└───┬──────────────────────┬──────────────────────────┬──────────────────┘
    │ Telegram Bot API     │ Africa's Talking          │ REST / WebSocket
    │ (async webhooks)     │ SMS + USSD webhooks       │
    ▼                      ▼                           ▼
┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────────────┐
│ TELEGRAM CHANNEL │ │ GSM CHANNEL      │ │ COMMAND CENTER (Next.js 14+)│
│ • Onboarding &   │ │ (feature phones, │ │ • Live Watch map (MapLibre) │
│   profiling      │ │  zero internet)  │ │ • Trigger polygons heatmap  │
│ • Proactive rich │ │ • SMS alert      │ │ • Community Sentinel layer  │
│   alerts         │ │   broadcasts     │ │ • Financing Triggers page   │
│ • Grounded Q&A   │ │ • SMS keyword    │ │ • 1-click Proof of Risk     │
│ • Photo/text     │ │   reporting      │ │ Delivered as: standalone    │
│   hazard reports │ │ • USSD *384#     │ │ web app, Telegram Mini App, │
│ (Swahili/English)│ │   session menu   │ │ offline-capable PWA, and    │
└──────────────────┘ └──────────────────┘ │ Android APK (Capacitor)     │
                                          └─────────────────────────────┘
```

**Technology stack:**

| Layer | Technology | Why |
|---|---|---|
| Frontend | [Next.js 14+](https://nextjs.org/), React, TypeScript | SSR dashboard, deployable as Telegram Mini App |
| Maps | [MapLibre GL JS](https://maplibre.org/) (or [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/)) | Vector-tile GIS rendering on mobile |
| Backend | Python 3.11, [FastAPI](https://fastapi.tiangolo.com/) | Async webhooks, first-class geospatial/scientific Python ecosystem |
| Database | [Supabase](https://supabase.com/) (PostgreSQL 15 + [PostGIS](https://postgis.net/) + [pgvector](https://github.com/pgvector/pgvector)) | Geospatial queries + embeddings + auth + realtime in one managed service |
| LLM | [Google Gemini 2.x](https://ai.google.dev/) (function calling + vision) | Multilingual (Swahili/Amharic), multimodal report processing |
| Bot framework | [aiogram 3](https://docs.aiogram.dev/) (or [python-telegram-bot](https://python-telegram-bot.org/)) | Async-native Telegram Bot API framework |
| SMS & USSD | [Africa's Talking](https://africastalking.com/) ([SMS API](https://developers.africastalking.com/docs/sms/overview), [USSD API](https://developers.africastalking.com/docs/ussd/overview)) | GSM-channel alerts, keyword reporting, and interactive USSD menus for feature phones — with a free [sandbox + simulator](https://developers.africastalking.com/simulator) for development |
| Mobile packaging | [Capacitor](https://capacitorjs.com/) + [next-pwa](https://github.com/shadowwalker/next-pwa) | Same Next.js codebase ships as installable offline-capable PWA and Android APK |
| Climate data | [xarray](https://docs.xarray.dev/), [xclim](https://xclim.readthedocs.io/) / [climate_indices](https://github.com/monocongo/climate_indices), [geopandas](https://geopandas.org/), [rioxarray](https://corteva.github.io/rioxarray/) | NetCDF/Zarr processing, SPI computation, zonal statistics |
| PDF | [WeasyPrint](https://weasyprint.org/) (HTML→PDF) | Templated Proof of Risk dossiers |
| Deploy | Docker + [Railway](https://railway.app/) / [Fly.io](https://fly.io/) / [Render](https://render.com/) | Fast, cheap, public HTTPS for webhooks & Mini App |

---

## 6. ICPAC Data Infrastructure: What We Integrate With

This section is the heart of Linda Node's technical credibility: we build directly on ICPAC's **published, open-source** anticipatory action tooling, cited accurately.

### 6.1 The `ibf-thresholds-triggers` pipeline (primary upstream)

Repo: **[icpac-igad/ibf-thresholds-triggers](https://github.com/icpac-igad/ibf-thresholds-triggers)** — "Thresholds and triggers for early warning action for drought hazard."

Actual contents (verified against the repository):

| Component | Purpose |
|---|---|
| `01_fcst_data_process.py` | Processes ECMWF SEAS51 forecast data |
| `02_prob_plot_q.py` | Plots quantile-based threshold exceedance probabilities |
| `03_prob_csv_q.py` | Exports exceedance probabilities to CSV |
| `04_metrics_csv_q.py` | Computes trigger metrics |
| `05_table_plot.py` | Renders trigger summary tables |
| `dask_routines.py` | [Dask](https://www.dask.org/) routines for scalable processing of large climate datasets |
| Notebook `01-input-spi-seas51` | SPI calculation from SEAS51 seasonal forecasts |
| Notebook `02-input-spi-chirps` | SPI calculation from CHIRPS observations |
| `run_map.py` | Stamp-plot maps of SPI for forecast ensemble members, CHIRPS observations, and threshold-exceedance empirical probabilities from NetCDF files |

**How Linda Node consumes it:** our ingestion worker ([Section 7.4](#74-data-ingestion-pipeline)) runs/consumes this pipeline's outputs — per-admin-unit threshold exceedance probabilities — and loads them into PostGIS, where the Predictive Monitor Agent evaluates them against trigger levels.

### 6.2 Discovered live API surface on Thresholds Watch (verified July 18, 2026)

The operational [Thresholds & Triggers Watch](https://eatriggersthresholds.icpac.net/) platform exposes a **publicly readable JSON API and vector-tile server** — meaning Linda Node can consume ICPAC's *live operational data*, not synthetic samples:

| Endpoint | Returns (verified) |
|---|---|
| `GET /api/datasets/` | Registry root: links to categories, sources, seasons, indicators |
| `GET /api/datasets/indicators/` | 6 indicators incl. **SPI-3 (CHIRPS)** with `supports_forecast: true`, SPI-3 (ERA5), SPEI-3 (ERA5) |
| `GET /api/datasets/sources/` | CHIRPS (0.05°, monthly), ERA5 (0.25°, daily), GHACOF (seasonal) |
| `GET /api/datasets/seasons/` | MAM, JJAS, **OND (release months: July–September — i.e., live during this hackathon)** |
| `GET /api/datasets/temp-forecast/metadata/` | Live forecast init dates (latest: 2026-06-28 at time of verification) |
| `GET /tileserv/index.json` | [pg_tileserv](https://github.com/CrunchyData/pg_tileserv) layer list: **GADM 4.1 admin boundaries levels 0–4**, IGAD clusters, child-vulnerability exposure scores, flood grids — consumable as vector tiles (MVT) |
| `/api/climate/area-analysis/popup_data/`, `/climate/api/pixel_timeseries/`, `/api/skill`, `/api/mapserver/proxy/` | Per-area values / time series / forecast skill (parameters to be reverse-engineered from the app during Phase 1) |

**Implications for the build:** boundaries can come straight from ICPAC's own tile server (`boundary.gadm_41_admin_level_*`); trigger/indicator values from the datasets API; and the demo can truthfully say *"this is ICPAC's live operational data"* — while keeping the offline seeded dataset as a fallback if endpoints change or rate-limit.

### 6.3 Upstream raw data sources

| Source | What | Access |
|---|---|---|
| **ECMWF SEAS5/SEAS51** | Seasonal ensemble forecasts (51 members, monthly, ~7-month lead) | [Copernicus Climate Data Store — seasonal-monthly-single-levels](https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels) (free account + [CDS API](https://cds.climate.copernicus.eu/how-to-api)) |
| **CHIRPS 2.0** | Quasi-global rainfall observations, 1981–present, 0.05° | [UCSB Climate Hazards Center](https://www.chc.ucsb.edu/data/chirps) · [direct data](https://data.chc.ucsb.edu/products/CHIRPS-2.0/) |
| **Admin boundaries (GHA)** | Sub-national polygons for trigger zones | [ICPAC GeoPortal](https://geoportal.icpac.net/) · [geoBoundaries](https://www.geoboundaries.org/) · [GADM](https://gadm.org/) |
| **SPI methodology** | Standardized Precipitation Index (WMO standard drought index) | [WMO SPI User Guide](https://library.wmo.int/idurl/4/39629) · computed via [climate_indices](https://github.com/monocongo/climate_indices) or [xclim](https://xclim.readthedocs.io/) |

### 6.4 ICPAC operational platforms we align with

| Platform | URL | Relationship to Linda Node |
|---|---|---|
| **Thresholds & Triggers Watch** | https://eatriggersthresholds.icpac.net/ | The operational platform exposing spatially-variable triggers/thresholds at subnational level. **Linda Node is the last-mile delivery layer for exactly this data.** |
| **Husika** | https://husika.icpac.net/ | ICPAC's digital last-mile early-warning communication platform. Linda Node is architected as a future Husika module ([roadmap](#14-future-roadmap-post-hackathon)). |
| **Hazard Watch** | https://hazardwatch.icpac.net/ | Multi-hazard monitoring & early warning products; contextual overlays. |
| **Drought Watch** | https://droughtwatch.icpac.net/ | Drought indicators; source for Command Center overlays and RAG context. |
| **ICPAC GeoPortal** | https://geoportal.icpac.net/ | Regional geospatial datasets incl. admin boundaries. |
| **ICPAC main site** | https://www.icpac.net/ | Seasonal forecasts, GHACOF statements, bulletins → RAG corpus. |
| **arco-ibf** | https://github.com/icpac-igad/arco-ibf | ICPAC's Analysis-Ready Cloud-Optimized DevOps routines for impact-based forecasting — the direction of travel for production data access. |
| **ICPAC GitHub org** | https://github.com/icpac-igad | All open-source tooling. |

---

## 7. Implementation Guide (For Developers & AI Agents)

> **This section is a build specification.** A developer — or an AI coding agent — should be able to implement Linda Node end-to-end from here without further clarification. Where a choice is open, the default is stated. Scope discipline: build exactly the MVP defined in [Section 10](#10-development-status-build-plan--milestones); everything else is roadmap.

### 7.1 Repository Layout

```
Linda-Node/
├── README.md                  # this file — the source of truth
├── LICENSE
├── docker-compose.yml         # local dev: api + worker + db
├── backend/
│   ├── pyproject.toml         # deps: fastapi, aiogram, supabase, geopandas,
│   │                          #  xarray, rioxarray, xclim, google-genai, weasyprint
│   ├── app/
│   │   ├── main.py            # FastAPI app, routers, webhook registration
│   │   ├── config.py          # pydantic-settings; all env vars typed here
│   │   ├── db.py              # Supabase/asyncpg client, PostGIS helpers
│   │   ├── models.py          # pydantic schemas mirroring DB tables
│   │   ├── bot/
│   │   │   ├── handlers.py    # aiogram routers: /start, onboarding, Q&A, reports
│   │   │   ├── keyboards.py   # inline keyboards & Mini App buttons
│   │   │   └── i18n.py        # sw/en string tables
│   │   ├── channels/
│   │   │   ├── sms.py         # Africa's Talking SMS: outbound broadcasts + inbound webhook
│   │   │   ├── ussd.py        # Africa's Talking USSD: session state machine (CON/END)
│   │   │   └── dispatch.py    # channel-agnostic alert dispatcher (telegram|sms|ussd)
│   │   ├── agents/
│   │   │   ├── monitor.py     # Predictive Monitor Agent
│   │   │   ├── context.py     # RAG Context Agent (pgvector retrieval)
│   │   │   ├── router.py      # Action Router Agent (alert drafting/dispatch)
│   │   │   └── prompts.py     # ALL system prompts, versioned (see 7.5)
│   │   ├── ingest/
│   │   │   ├── triggers.py    # parse ibf-thresholds-triggers outputs → PostGIS
│   │   │   ├── boundaries.py  # load admin polygons (GeoPortal/geoBoundaries)
│   │   │   └── bulletins.py   # scrape/load ICPAC bulletins → chunks → pgvector
│   │   ├── financing/
│   │   │   ├── triangulate.py # consensus check (Section 8)
│   │   │   └── dossier.py     # Proof of Risk PDF (WeasyPrint template)
│   │   └── api/
│   │       └── routes.py      # REST endpoints for dashboard (see 7.7)
│   └── tests/                 # pytest; fixtures with sample NetCDF/CSV
├── frontend/
│   ├── package.json           # next, react, maplibre-gl, @twa-dev/sdk
│   └── src/
│       ├── app/
│       │   ├── page.tsx       # Live Watch map
│       │   ├── financing/     # Financing Triggers page
│       │   └── api/           # route handlers proxying backend
│       ├── components/
│       │   ├── HazardMap.tsx  # MapLibre map: trigger polygons + report pins
│       │   ├── TriggerLight.tsx # red/amber/green county status
│       │   └── DossierButton.tsx
│       └── lib/telegram.ts    # Mini App init (@twa-dev/sdk)
├── data/                      # gitignored; sample NetCDF/CSV/GeoJSON for dev
└── scripts/
    ├── seed_demo.py           # demo data: 3 counties, 1 breached trigger
    └── run_pipeline.sh        # fetch sample data + run ICPAC pipeline steps
```

### 7.2 Environment & Setup

```bash
# 1. Clone & configure
git clone https://github.com/<you>/Linda-Node && cd Linda-Node
cp .env.example .env    # fill in the vars below

# 2. Backend
cd backend && pip install -e . && uvicorn app.main:app --reload

# 3. Frontend
cd frontend && npm install && npm run dev

# 4. Local tunnel for Telegram webhooks during dev
ngrok http 8000   # then: POST https://api.telegram.org/bot<TOKEN>/setWebhook?url=<ngrok-url>/telegram/webhook
```

**Required environment variables (`.env`):**

| Var | Purpose | Where to get it |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot auth | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `GEMINI_API_KEY` | LLM calls | [Google AI Studio](https://aistudio.google.com/) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | DB access | [Supabase dashboard](https://supabase.com/dashboard) → project settings |
| `DATABASE_URL` | Direct asyncpg/PostGIS | Supabase → connection string |
| `AT_USERNAME`, `AT_API_KEY` | Africa's Talking SMS/USSD (`sandbox` username in dev) | [Africa's Talking dashboard](https://account.africastalking.com/) |
| `AT_SHORTCODE`, `AT_USSD_CODE` | Sender ID / service code | Africa's Talking (sandbox codes free) |
| `CDSAPI_URL`, `CDSAPI_KEY` | SEAS51 download (optional if using sample data) | [CDS API how-to](https://cds.climate.copernicus.eu/how-to-api) |
| `MAPTILER_KEY` or `MAPBOX_TOKEN` | Basemap tiles | [MapTiler](https://www.maptiler.com/) / [Mapbox](https://mapbox.com/) |
| `PUBLIC_BASE_URL` | Webhook + Mini App URL | your deployment URL |

**Enable PostGIS + pgvector in Supabase (SQL editor):**
```sql
create extension if not exists postgis;
create extension if not exists vector;
```

### 7.3 Database Schema

```sql
-- Admin units: sub-national polygons for the Greater Horn of Africa
create table admin_units (
  id            bigserial primary key,
  country_iso3  text not null,            -- e.g. 'KEN', 'ETH', 'UGA'
  name          text not null,            -- e.g. 'Turkana', 'Karamoja'
  admin_level   int  not null,            -- 1 = county/region, 2 = sub-county
  geom          geometry(MultiPolygon, 4326) not null
);
create index admin_units_geom_idx on admin_units using gist (geom);

-- Trigger states: output of the ICPAC pipeline, per unit per issue date
create table trigger_states (
  id                 bigserial primary key,
  admin_unit_id      bigint references admin_units(id),
  issue_date         date not null,       -- forecast issue month
  valid_season       text not null,       -- e.g. 'OND 2026', 'MAM 2027'
  indicator          text not null default 'SPI3',
  exceedance_prob    numeric not null,    -- P(SPI3 < threshold), 0..1
  threshold_quantile numeric not null,    -- e.g. 0.33 (moderate), 0.20 (severe)
  trigger_level      text not null check (trigger_level in ('none','watch','action','severe')),
  source             text not null default 'ibf-thresholds-triggers',
  created_at         timestamptz default now(),
  unique (admin_unit_id, issue_date, valid_season, threshold_quantile)
);

-- Users: Telegram-registered community members & officials
create table users (
  id             bigserial primary key,
  telegram_id    bigint unique,                      -- null for SMS/USSD-only users
  phone_number   text unique,                        -- E.164; null for Telegram-only users
  channel        text not null default 'telegram'
                 check (channel in ('telegram','sms','ussd')),  -- preferred alert channel
  role           text not null check (role in ('farmer','pastoralist','official','ngo')),
  language       text not null default 'en' check (language in ('en','sw')),
  location       geometry(Point, 4326),              -- GPS pin (Telegram) or ward centroid (USSD)
  admin_unit_id  bigint references admin_units(id),  -- resolved via ST_Contains or USSD menu pick
  created_at     timestamptz default now(),
  check (telegram_id is not null or phone_number is not null)
);

-- Community reports: the "Community Sentinel" layer
create table reports (
  id            bigserial primary key,
  user_id       bigint references users(id),
  raw_text      text,
  photo_file_id text,                     -- Telegram file_id
  category      text,                     -- LLM-classified: 'water','pasture','crop','livestock','flood','other'
  severity      int check (severity between 1 and 5),
  ai_summary    text,
  location      geometry(Point, 4326),
  admin_unit_id bigint references admin_units(id),
  verified      boolean default false,    -- passed AI plausibility check
  created_at    timestamptz default now()
);
create index reports_geom_idx on reports using gist (location);

-- Alerts: what the Action Router sent, to whom (auditability)
create table alerts (
  id               bigserial primary key,
  trigger_state_id bigint references trigger_states(id),
  user_id          bigint references users(id),
  message_text     text not null,
  language         text not null,
  delivered        boolean default false,
  created_at       timestamptz default now()
);

-- Proof of Risk dossiers
create table dossiers (
  id               bigserial primary key,
  admin_unit_id    bigint references admin_units(id),
  trigger_state_id bigint references trigger_states(id),
  report_count     int not null,          -- community consensus inputs
  status           text not null default 'draft'
                   check (status in ('draft','issued','approved','rejected')),
  pdf_path         text,
  issued_by        bigint references users(id),   -- the human who clicked
  created_at       timestamptz default now()
);

-- RAG corpus: ICPAC bulletins/advisories chunked + embedded
create table documents (
  id        bigserial primary key,
  source    text not null,               -- URL of bulletin/advisory
  chunk     text not null,
  embedding vector(768)                  -- Gemini text-embedding dimension
);
create index documents_embedding_idx on documents
  using hnsw (embedding vector_cosine_ops);
```

**Key spatial query** (resolve a user's pin to their trigger status — the heart of conversational Q&A):
```sql
select ts.*
from trigger_states ts
join admin_units au on au.id = ts.admin_unit_id
where ST_Contains(au.geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
order by ts.issue_date desc
limit 1;
```

### 7.4 Data Ingestion Pipeline

**Goal:** trigger-state rows in PostGIS from ICPAC's pipeline outputs. Three supported paths — **build Path 0 first** (live operational data, verified available in [§6.2](#62-discovered-live-api-surface-on-thresholds-watch-verified-july-18-2026)), keep Path A as the demo-safe fallback, add Path B only if time allows.

**Path 0 — consume the live Thresholds Watch API (preferred):**
1. Pull boundaries as vector tiles / from the `boundary.gadm_41_admin_level_*` layers on `https://eatriggersthresholds.icpac.net/tileserv/` (or download GADM 4.1 directly and match IDs).
2. Poll `GET /api/datasets/temp-forecast/metadata/` for the latest init date; fetch per-area indicator values via the `area-analysis`/`pixel_timeseries` endpoints (reverse-engineer exact params from the app's network calls during Phase 1).
3. Map returned SPI-3/exceedance values to `trigger_states` rows exactly as in Path A step 2. Cache all responses; if any endpoint is unavailable or rate-limited, fall back to Path A seeded data automatically and label the data source in the UI honestly.

**Path A — consume pipeline outputs (MVP default):**
1. Obtain sample outputs of [ibf-thresholds-triggers](https://github.com/icpac-igad/ibf-thresholds-triggers): the CSV exceedance-probability files produced by `03_prob_csv_q.py` and/or the NetCDF SPI fields from the `01-input-spi-seas51` notebook. If live samples aren't published, generate them by running the notebooks on a small SEAS51 extract from the [CDS](https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels) (subset: Greater Horn of Africa bbox `[lat 15..-12, lon 21..52]`, 1 issue month, precipitation only) — or construct a clearly-labeled synthetic sample with realistic values for the demo.
2. `ingest/triggers.py`: parse CSV/NetCDF with pandas/xarray → map each row to an `admin_unit` (spatial join via geopandas `sjoin` for gridded data, or name-matching for tabular) → classify `trigger_level`:
   - `exceedance_prob ≥ 0.6` at severe quantile (0.20) → **severe**
   - `≥ 0.5` at moderate quantile (0.33) → **action**
   - `≥ 0.35` at moderate quantile → **watch**
   - else → **none**
   (Trigger levels are configurable constants — cite the [Thresholds Watch](https://eatriggersthresholds.icpac.net/) methodology in the demo; do not present these defaults as ICPAC-official.)
3. Upsert into `trigger_states`. Run on a schedule (cron/`asyncio` task) and expose `POST /ingest/run` for manual demo triggering.

**Path B — run the ICPAC pipeline live (stretch):** wrap `01_fcst_data_process.py` → `03_prob_csv_q.py` in `scripts/run_pipeline.sh` with pinned deps; document runtime and data volume honestly.

**Boundaries:** load admin-1/admin-2 polygons for at least Kenya + Uganda + Ethiopia from the [ICPAC GeoPortal](https://geoportal.icpac.net/) (preferred — ICPAC's own boundaries) or [geoBoundaries](https://www.geoboundaries.org/) into `admin_units` via `ingest/boundaries.py` (geopandas → PostGIS with `to_postgis`).

**RAG corpus:** `ingest/bulletins.py` pulls 10–30 public ICPAC documents (seasonal forecast statements, [GHACOF](https://www.icpac.net/ghacof/) communiqués, drought advisories from [icpac.net](https://www.icpac.net/)), chunks ~500 tokens, embeds with Gemini `text-embedding-004`, stores in `documents`.

### 7.5 The Multi-Agent System

All prompts live in `backend/app/agents/prompts.py`, versioned as constants. Use Gemini **function calling / structured output** (JSON mode) for every agent — never parse free text.

**Agent 1 — Predictive Monitor** (`monitor.py`)
- **Trigger:** runs after each ingestion; also on-demand.
- **Logic (deterministic first, LLM second):** SQL selects `trigger_states` rows where `trigger_level in ('action','severe')` and no alert has been sent for that (unit, issue_date). *The threshold comparison itself is pure code* — the LLM never decides whether a trigger fired. The LLM is used to rank/summarize: given the flagged units + recent report density, produce a JSON priority queue `[{admin_unit_id, urgency: 1-5, rationale}]`.
- **System prompt sketch:** *"You are the Predictive Monitor for an anticipatory-action system in the Greater Horn of Africa. You are given already-computed drought trigger exceedances from ICPAC's pipeline. You never alter probabilities. Rank the flagged units by urgency for alert dispatch, considering severity, population role mix, and community report density. Respond only in the provided JSON schema."*

**Agent 2 — RAG Context** (`context.py`)
- **Input:** a flagged admin unit + user profile (role, language).
- **Retrieval:** embed the query ("drought outlook {unit} {season} advice for {role}"), cosine top-k=6 from `documents`, plus the latest 10 verified community reports in that unit.
- **Output (JSON):** `{regional_context, seasonal_advice[], indigenous_signals[], sources[]}` — every claim must carry its source URL; if retrieval is empty, say so rather than inventing context. This structured context is handed to Agent 3.

**Agent 3 — Action Router** (`router.py`)
- **Input:** trigger state + context JSON + target user profile.
- **Output (JSON):** `{message_text, language, buttons[]}` where `message_text` is ≤ 600 chars, in the user's language, livelihood-specific, and contains: (1) what is forecast, with probability in plain words ("8 out of 10 model runs"), (2) 2–3 concrete actions, (3) the data source ("ICPAC seasonal forecast").
- **Dispatch:** writes an `alerts` row, sends via Bot API with inline keyboard `[Open Hazard Map] [Report Local Conditions]`.
- **Safety rails in prompt:** never exaggerate certainty; never promise financing; always attribute the forecast to ICPAC; if trigger_level is `watch`, use advisory language, not alarm.

**Conversational Q&A** (in `bot/handlers.py`, reusing Agents 2+3): user free-text question → geocode = their stored pin → the spatial query in 7.3 fetches trigger state → RAG context → Gemini composes a grounded answer. **Every answer states the admin unit and forecast issue date it's based on.** If the user has no pin, ask for one.

**Report processing** (Community Sentinel): incoming text/photo → Gemini multimodal classification into `{category, severity, ai_summary, plausible: bool}` → store in `reports` with the user's location; `verified = plausible`. Photos fetched via Telegram `getFile`.

### 7.6 Telegram Bot: Commands & Conversation Flows

| Command / entry | Flow |
|---|---|
| `/start` | Welcome (en/sw toggle) → role selection via inline keyboard: 🌾 Farmer / 🐄 Pastoralist / 🏛 Official / 🤝 NGO → request location pin (Telegram location share) → resolve `admin_unit` via `ST_Contains` → confirmation: *"You are registered in **Turkana**. You will receive drought early-warning alerts for this area."* |
| `/status` | Current trigger state for user's unit, in plain language, with issue date + source |
| `/report` | *"Describe what you see (text or photo)"* → multimodal classification → *"Thank you. Your report about **pasture conditions** was added to the community map."* |
| `/map` | Button opening the Mini App (officials/NGO see financing page too) |
| `/language` | en ↔ sw |
| Free text | Grounded Q&A flow (7.5) |
| Proactive alert | Pushed by Action Router when a trigger fires; buttons: `[Open Hazard Map]` `[Report Local Conditions]` |

**Alert copy example (what judges will see in the demo):**
> ⚠️ **Linda Node Alert — Turkana**
> ICPAC's seasonal forecast (issued July 2026) shows a **high chance (≈80%) of severely below-normal rains** for Oct–Dec.
> **Recommended now:** ① Consider selling excess livestock while market prices hold. ② Store fodder and water. ③ Register for county drought support.
> *Source: ICPAC SEAS51 trigger, SPI-3.* `[Open Hazard Map]` `[Report Local Conditions]`

### 7.7 Backend API Endpoints

| Method & path | Purpose | Consumer |
|---|---|---|
| `POST /telegram/webhook` | All bot updates (aiogram dispatcher) | Telegram |
| `POST /channels/sms/webhook` | Inbound SMS (keyword reports, STOP/START) | Africa's Talking |
| `POST /channels/ussd/webhook` | USSD session steps (form-encoded; respond `CON`/`END` plain text) | Africa's Talking |
| `POST /channels/sms/delivery` | SMS delivery reports → mark `alerts.delivered` | Africa's Talking |
| `GET /api/triggers?season=&level=` | GeoJSON FeatureCollection of admin polygons + trigger properties | Dashboard map |
| `GET /api/reports?unit_id=&since=` | GeoJSON of verified community reports | Dashboard map |
| `GET /api/units/{id}/summary` | Trigger history + report stats + latest context for one unit | Unit drill-down |
| `POST /api/dossiers` | Generate Proof of Risk for a unit (auth: official/NGO role) | Financing page |
| `GET /api/dossiers/{id}.pdf` | Download rendered dossier | Financing page |
| `POST /ingest/run` | Manually run ingestion (demo lever) | Ops/demo |
| `GET /healthz` | Liveness | Deploy platform |

Auth for MVP: Telegram `initData` validation for Mini App requests ([spec](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)); a simple signed session for the standalone dashboard.

### 7.8 The Command Center Dashboard & Mini App

**Page 1 — Live Watch Map (`/`):**
- MapLibre GL, dark style, centered on the Greater Horn of Africa.
- **Choropleth layer:** admin polygons colored by `trigger_level` (none = neutral, watch = yellow, action = orange, severe = red) from `GET /api/triggers`.
- **Community Sentinel layer:** clustered pins from `GET /api/reports`; click → popup with `ai_summary`, category icon, time.
- Click a polygon → side panel from `GET /api/units/{id}/summary`: probability, SPI indicator, report count, last alert sent.

**Page 2 — Financing Triggers (`/financing`):**
- Table of units at `action`/`severe`, traffic-light status chips, report-consensus count, triangulation check result.
- **"Generate Action Brief & Risk Certificate"** button per row → `POST /api/dossiers` → download link. Disabled (with explanation) when triangulation fails — *show this in the demo; the refusal is a feature.*

**Mini App packaging:** same Next.js app detected via [`@twa-dev/sdk`](https://github.com/twa-dev/SDK); register the URL with BotFather (`/newapp`). Must be mobile-first — judges will open it on phones.

### 7.9 Proof of Risk Dossier Generation

A dossier is a **decision-support evidence package, not a payment instruction**. Generated server-side by WeasyPrint from an HTML template. Contents:

1. **Header:** unit name, country, generation timestamp, dossier ID, status (`draft`/`issued`).
2. **Official trigger evidence:** indicator (SPI-3), exceedance probability, threshold quantile, forecast issue date & valid season, source pipeline ([ibf-thresholds-triggers](https://github.com/icpac-igad/ibf-thresholds-triggers)) — with the map snapshot of the unit.
3. **Community consensus:** count + category breakdown of verified reports in the window, sample AI summaries (anonymized).
4. **Triangulation result:** the three-condition check ([Section 8](#8-system-resiliency--security-safeguards)) with pass/fail per condition.
5. **AI-drafted situation analysis:** 200 words, every sentence attributable to items 2–4.
6. **Recommended anticipatory actions & indicative costing** (from RAG context).
7. **Authorization block:** *"This dossier supports — but does not constitute — a financing decision. Final authorization: ____________ (name, organization, signature)."*
8. **Footer:** links to [Thresholds Watch](https://eatriggersthresholds.icpac.net/), the [IGAD AA Roadmap](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf), and this repository.

### 7.10 SMS & USSD Channel (Africa's Talking)

The GSM channel makes Linda Node work on **any phone, with zero internet** — the decisive reach argument for pastoralist households. Built on [Africa's Talking](https://africastalking.com/) ([SMS docs](https://developers.africastalking.com/docs/sms/overview), [USSD docs](https://developers.africastalking.com/docs/ussd/overview)); develop against the free **sandbox + [simulator](https://developers.africastalking.com/simulator)**, demo on sandbox or a live shortcode if provisioning time allows.

**Environment variables:** `AT_USERNAME` (use `sandbox` in dev), `AT_API_KEY`, `AT_SHORTCODE`, `AT_USSD_CODE`.

**Outbound SMS alerts** (`channels/sms.py` + `channels/dispatch.py`):
- The Action Router produces the alert once; `dispatch.py` routes per `users.channel`. For SMS users the LLM is instructed to compress to **≤ 160 GSM-7 chars**, action-first: `LINDA: Ukame mkali unatarajiwa Turkana Okt-Des (ICPAC). Uza mifugo ya ziada sasa; hifadhi malisho. Jibu REPORT <hali> kutuma taarifa.`
- Delivery reports hit `POST /channels/sms/delivery` → set `alerts.delivered`.

**Inbound SMS keywords** (webhook `POST /channels/sms/webhook`):
- `REPORT <free text>` → same Gemini classification pipeline as Telegram reports; location = registered ward centroid.
- `STATUS` → current trigger state for the user's unit, compressed.
- `STOP` / `START` → opt-out/in (required for responsible messaging).

**USSD session menu** (`channels/ussd.py` — a small state machine keyed on `sessionId`; AT posts `sessionId, serviceCode, phoneNumber, text` after each step; respond with plain text starting `CON` to continue or `END` to finish):

```
*384*XXX#
CON Karibu Linda Node / Welcome
 1. Hali ya hewa eneo langu (My area outlook)
 2. Jisajili (Register)
 3. Ripoti hali (Report conditions)
 4. Badilisha lugha (Language)

[2] → CON Chagua kaunti / county list (paged)   → CON role: 1.Mkulima 2.Mfugaji
     → END Umesajiliwa Turkana. Utapokea tahadhari kwa SMS.
[1] → END Turkana: Uwezekano mkubwa (80%) wa mvua chache Okt-Des (ICPAC).
     Hatua: uza mifugo ya ziada, hifadhi malisho.
[3] → CON Eleza hali (1.Malisho 2.Maji 3.Mazao 4.Mifugo) → END Asante. Ripoti imepokelewa.
```

- USSD registration stores `phone_number` + county pick (ward centroid as location, `channel='sms'` so subsequent alerts arrive by SMS — USSD is session-only, it cannot receive pushes).
- Keep every USSD screen ≤ 160 chars; no LLM calls inside the session (latency limit ~8s) — serve from pre-computed `trigger_states` + cached advice strings.

### 7.11 PWA & Android APK Packaging (Offline Functionality)

One Next.js codebase ships four ways — satisfying the hackathon's "web link **or APK**" requirement with both:

1. **Web dashboard** — standard deployment (Vercel or same host as API).
2. **Telegram Mini App** — same app detected via `@twa-dev/sdk` ([§7.8](#78-the-command-center-dashboard--mini-app)).
3. **Installable PWA** — via [next-pwa](https://github.com/shadowwalker/next-pwa): web manifest + service worker with `stale-while-revalidate` caching of `GET /api/triggers`, `GET /api/units/{id}/summary`, advisory text, and map tiles for the user's region. Result: **the last-synced trigger map and advice remain fully readable offline** in the field; an offline banner shows the data's sync timestamp (honesty rule: never present cached data as live).
4. **Android APK** — [Capacitor](https://capacitorjs.com/) wraps the same build (`npx cap add android && npx cap sync && gradle assembleRelease`). The APK bundles the service-worker cache plus a local fallback page, and registers for background sync to refresh trigger states when connectivity returns.

Offline scope is deliberately read-only at MVP: viewing warnings/maps works offline; submitting reports queues locally (IndexedDB) and syncs when back online.

### 7.12 Deployment

- **Backend:** Docker image → Railway/Fly/Render. Needs public HTTPS for the Telegram webhook. Set webhook on deploy: `setWebhook?url=$PUBLIC_BASE_URL/telegram/webhook&secret_token=...` (verify the secret header in the handler).
- **Frontend:** Vercel (or same host). `NEXT_PUBLIC_API_URL` → backend.
- **DB:** Supabase cloud (free tier suffices for MVP).
- **Demo resilience:** `scripts/seed_demo.py` seeds 3 counties (1 severe, 1 watch, 1 none), 12 community reports, 2 registered demo users — so the demo never depends on live external downloads. Record the video against seeded data; *say so honestly*.

---

## 8. System Resiliency & Security Safeguards

**Data Integrity & Fraud Mitigation — the Triangulation Engine.** No Proof of Risk dossier is issued on isolated data. `financing/triangulate.py` requires all three:

```
Condition 1: OFFICIAL   — latest trigger_state for the unit has trigger_level ∈ {action, severe}
Condition 2: COMMUNITY  — ≥ K verified reports (default K=5) in the unit within the last 21 days,
                          from ≥ K/2 distinct users (anti-sybil)
Condition 3: PLAUSIBLE  — LLM verification pass: reports are consistent with the hazard type
                          (e.g., pasture-failure reports during a drought trigger, not flood reports)
```

Failing any condition blocks issuance and the UI explains which condition failed. This prevents malicious or erroneous crowdsourced reporting from exploitatively supporting capital release — and the final authorization always rests with a named human at the NGO/cooperative (the dossier's authorization block).

**Prompt-injection & content safety:** community reports are untrusted input. They are (a) processed only through structured-output classification calls, never concatenated into system prompts, and (b) rendered escaped in dashboards. Alert-drafting prompts forbid financial promises and certainty inflation.

**Asynchronous spatial data processing:** heavy meteorological files (NetCDF/Zarr) are parsed out-of-band by the ingestion worker and stored as query-optimized PostGIS records, so user-facing queries run in milliseconds. (ICPAC's own `dask_routines.py` demonstrates the scaling path for full-resolution data.)

**Auditability:** every alert, report, and dossier is a database row with timestamps and actor IDs — an NGO can reconstruct exactly why any alert or dossier was produced.

**Low-connectivity resilience (built-in):** Linda Node runs a **dual-layer communications architecture**. The rich-media layer (Telegram + Mini App) is itself lightweight on degraded networks; beneath it, the GSM layer via [Africa's Talking](https://africastalking.com/) delivers SMS alert broadcasts and an interactive USSD menu that work on feature phones with **zero internet** ([§7.10](#710-sms--ussd-channel-africas-talking)). On the smartphone side, the PWA/APK service worker keeps the last-synced trigger map and advisories readable fully offline, with queued report sync on reconnect ([§7.11](#711-pwa--android-apk-packaging-offline-functionality)). If cellular data collapses during a severe-weather event, warnings still flow over plain GSM.

---

## 9. Application Walkthrough (User Journeys)

### Journey 1 — Amina, pastoralist, Turkana (community member)
1. **Onboarding:** finds the bot via a county extension officer's shared link. `/start` → picks 🐄 Pastoralist + Kiswahili → shares location pin → registered to Turkana.
2. **Proactive alert (2 months before the shock):** receives the alert shown in [7.6](#76-telegram-bot-commands--conversation-flows) — in Swahili, pastoralist-specific (destocking + fodder, not maize planting).
3. **Q&A:** asks *"Je, ni salama kupanda mahindi wiki ijayo?"* → grounded answer for her exact pin, citing the ICPAC forecast issue date.
4. **Reporting:** sends a photo of failing pasture → classified `pasture / severity 4` → appears on the Community Sentinel layer within seconds.

### Journey 2 — Ekiru, herder with a feature phone, no internet (GSM channel)
1. **Registration:** at a community meeting, dials `*384*XXX#` on his 2G feature phone → picks Kiswahili → county: Turkana → role: Mfugaji (herder). No smartphone, no app, no data bundle needed.
2. **Proactive alert:** weeks later receives the 160-character SMS: *"LINDA: Ukame mkali unatarajiwa Turkana Okt-Des (ICPAC). Uza mifugo ya ziada sasa; hifadhi malisho."*
3. **Check-in:** dials the USSD code, presses 1, and reads the current outlook for his county on-screen — even with zero airtime for calls.
4. **Reporting:** replies `REPORT malisho yameisha` (pasture is finished) → classified and pinned to the Community Sentinel layer like any Telegram report — same triangulation weight, same dignity.

### Journey 3 — David, county drought officer (official)
1. Receives an escalation alert: Turkana entered **severe**. Taps `[Open Hazard Map]` → Mini App opens inside Telegram: red polygon, 14 community reports clustered in two wards.
2. Opens **Financing Triggers**: Turkana row shows traffic-light red, triangulation ✅✅✅. Clicks **Generate Action Brief & Risk Certificate**.
3. Downloads the PDF dossier and tables it with the county steering group and the NGO cash-transfer partner — **days before the failed season materializes**, converting a forecast into a funded response.

### Journey 4 — NGO program manager (anticipatory action financing)
1. Monitors the standalone dashboard across three countries. Sees which triggered units also have community-consensus confirmation (double evidence).
2. Uses dossiers as standardized annexes for activating pre-arranged anticipatory funds — the exact mechanism the [IGAD AA Roadmap](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf) and [Anticipation Hub](https://www.anticipation-hub.org/) frameworks call for.

---

## 10. Development Status, Build Plan & Milestones

**Honest status (updated 2026-07-18):** Linda Node is at the **design-and-architecture stage**. This README is the blueprint; no application code exists in the repo yet. The prototype is being built for the July 31 submission on the plan below. *(Any AI agent working in this repo: consult this table, build the earliest incomplete phase, and respect the scope cuts.)*

| Phase | Days | Deliverable | Acceptance criteria |
|---|---|---|---|
| **1. Data foundation** | 1–3 | Boundaries + trigger ingestion (Path A) into Supabase/PostGIS; seed script | `GET /api/triggers` returns real GeoJSON; spatial pin→unit query works |
| **2. Telegram bot MVP** | 3–8 | Onboarding, proactive alerts, grounded Q&A, report intake (en+sw) | A judge can register, receive an alert, ask a question, file a report — on their own phone |
| **3. SMS & USSD channel** | 6–9 | Africa's Talking integration: SMS broadcasts, keyword reports, USSD menu ([§7.10](#710-sms--ussd-channel-africas-talking)) — parallel track, team's core expertise | Register + receive alert + file report entirely from the AT simulator (or a feature phone on sandbox) |
| **4. Dashboard + Mini App + PWA/APK** | 8–11 | Live Watch map + Financing page; Mini App registration; next-pwa offline caching; Capacitor APK build ([§7.11](#711-pwa--android-apk-packaging-offline-functionality)) | Map renders on mobile inside Telegram; airplane-mode phone still shows last-synced triggers; APK installs and runs |
| **5. Proof of Risk** | 10–12 | Triangulation engine + PDF dossier | Button produces the full dossier; failing triangulation blocks with explanation |
| **6. Ship** | 11–13 | Deploy, seed demo data, record ≤5-min video, finalize README, submit | Submission complete on Devpost before July 31, 5pm EAT |

**Deliberately descoped to the roadmap** (do *not* build these for the hackathon): voice-note processing, Bluetooth mesh, Amharic and further languages, live SEAS51 downloads in production, the agent-activity feed, Celery/Redis (a scheduled asyncio task suffices at MVP scale), live USSD shortcode provisioning if telco lead times exceed the deadline (sandbox + simulator demo is acceptable and honest). Depth on a working slice beats breadth of promises.

---

## 11. Impact: Who Benefits and How We Measure It

**Beneficiaries:**
- **Agro-pastoral households** in drought-prone GHA counties: earlier, livelihood-specific, mother-tongue warnings → time to destock at fair prices, secure fodder/water, and protect assets.
- **County/sub-national officials:** a single view merging official triggers with ground truth, plus standardized evidence packages.
- **NGOs & AA financiers:** lower verification cost and faster, auditable activation of pre-arranged funds.
- **ICPAC/IGAD:** a reusable last-mile module that increases the real-world consumption of data they already produce.

**Why anticipatory action pays:** evaluations across the sector (see [Anticipation Hub evidence base](https://www.anticipation-hub.org/experience/evidence), [OCHA anticipatory action](https://www.unocha.org/anticipatory-action), [WFP anticipatory action](https://www.wfp.org/anticipatory-actions)) consistently find acting before a shock is several times more cost-effective than post-disaster response, and preserves household assets that would otherwise be sold in distress.

**Measurable indicators (built into the schema from day one):**

| Indicator | Source table |
|---|---|
| Registered users by role/unit/language | `users` |
| Alert reach & delivery rate; lead time (alert date vs. season onset) | `alerts` |
| Community reports volume, categories, verification rate | `reports` |
| Trigger-to-dossier conversion & time-to-dossier | `dossiers` |
| Q&A engagement (questions grounded-answered) | bot logs |

**Scalability:** the entire pipeline is admin-unit-generic — adding a country is a boundary-file import plus trigger coverage; the agents are language-parameterized; Telegram distribution has zero marginal install cost.

---

## 12. Alignment with Judging Criteria

### Technical Depth & Engineering (30%)
- Direct, **correctly-cited** consumption of ICPAC's real open-source trigger pipeline (SEAS51 → SPI → quantile threshold exceedance) rather than commercial weather APIs — see [Section 6](#6-icpac-data-infrastructure-what-we-integrate-with).
- Real geospatial engineering: PostGIS-indexed polygons, `ST_Contains` pin resolution, GeoJSON APIs, pgvector RAG, async webhook processing, Dockerized deploys — full spec in [Section 7](#7-implementation-guide-for-developers--ai-agents).
- Deterministic safety design: triggers and triangulation are code, not LLM judgment calls.

### Innovation & AI Creativity (30%)
- A **multi-agent ecosystem** (monitor → context → router) acting as geospatial translator and dispatcher — beyond standard RAG chatbot wrappers, with structured-output discipline throughout.
- **Telegram Mini Apps** delivering responsive GIS dashboards inside a chat client — changing how early-warning data is consumed in the field.
- The **Proof of Risk dossier**: AI-assembled, human-authorized evidence packages connecting triggers to anticipatory financing — the novel piece no generic weather bot has.
- **Epistemic inclusion:** multimodal AI turning community voice into a live verification layer for official science.

### Problem Value & Impact (25%)
- Attacks the economic barrier to anticipatory action — warnings without capital don't change outcomes ([Section 11](#11-impact-who-benefits-and-how-we-measure-it)).
- **Reach that matches regional reality:** USSD/SMS coverage means the poorest household with a 2G feature phone gets the same warning as a smartphone user — plus offline PWA/APK access where data networks degrade during crises.
- Institutionally aligned: [IGAD AA Roadmap](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf), [Husika's](https://husika.icpac.net/) last-mile mandate, and the live [IMPAACT initiative](https://www.actionagainsthunger.org/press-releases/action-against-hunger-and-the-igad-climate-prediction-and-applications-centre-icpac-launch-landmark-echo-funded-initiative-to-build-anticipatory-action-systems-across-the-greater-horn-of-africa/) region.
- Impact is instrumented, not asserted: the measurement tables ship with the MVP.

### Presentation & Documentation (15%)
- This README is the full picture — problem, architecture, build spec, honest status, impact model — with every external claim linked to its source, and both 250-word submission sections pre-written to spec.

---

## 13. Demo Video Plan & Submission Checklist

**Video (≤ 5 minutes) — shot list:**

| Time | Scene |
|---|---|
| 0:00–0:30 | The gap: ICPAC's [Thresholds Watch](https://eatriggersthresholds.icpac.net/) on screen → *"world-class triggers; now watch them reach a pastoralist's phone."* |
| 0:30–1:00 | Architecture slide (the diagram in [Section 5](#5-system-architecture)), 30 seconds max |
| 1:00–2:15 | **Phone screen recording:** onboarding → proactive Swahili alert arrives → grounded Q&A on the user's pin |
| 2:15–2:45 | Community report with photo → pin appears on the Live Watch map |
| 2:45–3:30 | **The reach story:** USSD `*384#` registration + SMS alert arriving on a feature phone (AT simulator or real device) → then a smartphone in **airplane mode** still showing the last-synced trigger map (PWA offline) |
| 3:30–4:15 | Official flow: Mini App opens inside Telegram → Financing page → triangulation passes → **PDF dossier generated on camera** |
| 4:15–4:40 | Show triangulation *failing* for a non-consensus county — the safety story |
| 4:40–5:00 | Impact + roadmap (Husika module), honest status statement, team |

**Submission checklist (Devpost, before July 31 2026, 5:00pm EAT):**
- [ ] Project Overview ≤ 250 words (copy from [Section 2](#2-the-problem))
- [ ] Solution Details ≤ 250 words (copy from [Section 3](#3-the-solution-linda-node))
- [ ] Working prototype URL (dashboard/PWA) + bot handle (@…bot) + APK download link + USSD/SMS demo access (sandbox instructions)
- [ ] Demo video ≤ 5 min uploaded (YouTube unlisted) and linked
- [ ] Public GitHub repo (this one) with reproducible setup ([7.2](#72-environment--setup))
- [ ] Tech stack listed on the form (from [Section 5](#5-system-architecture))
- [ ] All open-source tools acknowledged (rules requirement — [Section 15](#15-complete-resources-sources--references))
- [ ] Test the bot end-to-end from a phone that has never seen the project

---

## 14. Future Roadmap (Post-Hackathon)

- **Live USSD shortcode & premium SMS provisioning:** graduating from Africa's Talking sandbox to production telco shortcodes across all IGAD countries (dedicated codes, delivery SLAs, cost optimization at scale).
- **Voice-to-text for indigenous languages:** processing voice notes in localized dialects underserved by standard text models.
- **Amharic, Somali, Oromo language packs** beyond the launch Swahili/English.
- **Offline mesh networking:** relaying hazard warnings via Bluetooth mesh where cellular infrastructure collapses during floods.
- **Flood & multi-hazard triggers:** extending beyond drought as ICPAC's multi-hazard thresholds mature on [Hazard Watch](https://hazardwatch.icpac.net/).
- **Direct Husika API merger:** full backend integration to make Linda Node an official, out-of-the-box module for ICPAC's [Husika](https://husika.icpac.net/) platform by 2027.
- **arco-ibf alignment:** migrating ingestion to ICPAC's [analysis-ready cloud-optimized](https://github.com/icpac-igad/arco-ibf) data routines as they productionize.

---

## 15. Complete Resources, Sources & References

### Hackathon (Devpost)
- [Main page — criteria, prizes, judges](https://igad-husika-hackathon.devpost.com/)
- [Rules](https://igad-husika-hackathon.devpost.com/rules) · [Resources](https://igad-husika-hackathon.devpost.com/resources) · [Updates](https://igad-husika-hackathon.devpost.com/updates)
- Organizer contact: hackathon@icpac.net

### ICPAC platforms & data
- [ICPAC — main site](https://www.icpac.net/) · [GHACOF forums](https://www.icpac.net/ghacof/)
- [Thresholds & Triggers Watch](https://eatriggersthresholds.icpac.net/) — operational triggers/thresholds platform (our upstream)
- [Hazard Watch](https://hazardwatch.icpac.net/) · [Drought Watch](https://droughtwatch.icpac.net/)
- [Husika — last-mile early-warning communication](https://husika.icpac.net/)
- [ICPAC GeoPortal — boundaries & regional datasets](https://geoportal.icpac.net/)
- [icpac-igad/ibf-thresholds-triggers](https://github.com/icpac-igad/ibf-thresholds-triggers) — drought thresholds & triggers pipeline (SEAS51, CHIRPS, SPI)
- [icpac-igad/arco-ibf](https://github.com/icpac-igad/arco-ibf) — analysis-ready cloud-optimized IBF routines
- [ICPAC GitHub organization](https://github.com/icpac-igad)

### Climate data & science
- [Copernicus CDS — seasonal forecasts (SEAS5/51)](https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels) · [CDS API guide](https://cds.climate.copernicus.eu/how-to-api)
- [CHIRPS rainfall data — UCSB Climate Hazards Center](https://www.chc.ucsb.edu/data/chirps) · [direct downloads](https://data.chc.ucsb.edu/products/CHIRPS-2.0/)
- [WMO SPI User Guide](https://library.wmo.int/idurl/4/39629)
- [climate_indices (SPI library)](https://github.com/monocongo/climate_indices) · [xclim](https://xclim.readthedocs.io/) · [xarray](https://docs.xarray.dev/) · [geopandas](https://geopandas.org/) · [Dask](https://www.dask.org/)
- [geoBoundaries](https://www.geoboundaries.org/) · [GADM](https://gadm.org/)

### Anticipatory action policy & evidence
- [IGAD Regional Roadmap for Anticipatory Action (PDF)](https://www.icpac.net/documents/894/IGAD_RegionalAARoadmap-Revised.pdf)
- [IMPAACT initiative launch — Action Against Hunger × ICPAC, July 2026](https://www.actionagainsthunger.org/press-releases/action-against-hunger-and-the-igad-climate-prediction-and-applications-centre-icpac-launch-landmark-echo-funded-initiative-to-build-anticipatory-action-systems-across-the-greater-horn-of-africa/)
- [IGAD Disaster Risk Management Programme](https://www.icpac.net/our-projects/igads-disaster-risk-management-programme/)
- [Anticipation Hub](https://www.anticipation-hub.org/) · [evidence base](https://www.anticipation-hub.org/experience/evidence)
- [OCHA anticipatory action](https://www.unocha.org/anticipatory-action) · [WFP anticipatory action](https://www.wfp.org/anticipatory-actions)
- [Forecast-based financing for droughts — Mozambique study (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2405880723000055)
- [Well-designed triggers support decision-making for AA (PreventionWeb)](https://www.preventionweb.net/drr-community-voices/well-designed-triggers-support-decision-making-anticipatory-action)
- [Declaration of the First Eastern Africa Dialogue Platform on AA (ICPAC)](https://www.icpac.net/publications/declaration-from-the-first-eastern-africa-dialogue-platform-on-anticipatory-action/)

### Build tooling (acknowledged per hackathon rules)
- [Telegram Bot API](https://core.telegram.org/bots/api) · [Telegram Mini Apps](https://core.telegram.org/bots/webapps) · [@BotFather](https://t.me/BotFather) · [aiogram](https://docs.aiogram.dev/) · [python-telegram-bot](https://python-telegram-bot.org/) · [@twa-dev/sdk](https://github.com/twa-dev/SDK)
- [Google Gemini API](https://ai.google.dev/) · [Google AI Studio](https://aistudio.google.com/)
- [FastAPI](https://fastapi.tiangolo.com/) · [Next.js](https://nextjs.org/) · [Supabase](https://supabase.com/) · [PostGIS](https://postgis.net/) · [pgvector](https://github.com/pgvector/pgvector)
- [MapLibre GL JS](https://maplibre.org/) · [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/) · [MapTiler](https://www.maptiler.com/)
- [WeasyPrint](https://weasyprint.org/) · [Railway](https://railway.app/) · [Fly.io](https://fly.io/) · [Render](https://render.com/) · [Vercel](https://vercel.com/)
- [Africa's Talking](https://africastalking.com/) — [SMS API](https://developers.africastalking.com/docs/sms/overview) · [USSD API](https://developers.africastalking.com/docs/ussd/overview) · [sandbox simulator](https://developers.africastalking.com/simulator)
- [Capacitor (APK packaging)](https://capacitorjs.com/) · [next-pwa (offline PWA)](https://github.com/shadowwalker/next-pwa)

---

<div align="center">

**Linda Node** — *from world-class forecasts to funded action, before the disaster strikes.*

</div>
