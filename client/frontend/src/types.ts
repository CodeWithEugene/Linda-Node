import type { ActionCard, Role } from './api'

export type SourceSnapshot = {
  id: string
  adapter: string
  endpoint_url: string
  retrieved_at: string
  payload_sha256: string
  schema_ok: boolean
  freshness: Freshness
  meta?: {
    label?: string
    synthetic?: boolean
    escalation_step?: number
    schema_errors?: string[]
    last_error?: string
    fallback_reason?: string
    provenance?: { synthetic?: boolean; note?: string; source?: string }
    parts?: { url: string; sha256: string; bytes: number }[]
  }
  raw?: { available: boolean; truncated?: boolean; bytes?: number; preview?: string; note?: string }
  payload?: unknown
}

export type Freshness = 'live' | 'cached' | 'stale' | 'replay'

export type Signal = {
  id: string
  name: string
  area_id: string
  area_name?: string
  hazard?: string
  indicator: string
  indicator_name?: string
  probability?: number
  value?: number
  threshold_value?: number
  severity?: string
  status?: string
  snapshot_id: string
  freshness: Freshness
  source_adapter: string
  probability_source?: string
  valid_date?: string
}

export type UpstreamAction = {
  id: string
  name: string
  action_type: string
  status?: string
  area_name?: string
  scheduled_date?: string
}

export type CheckLog = {
  id: string
  check_date?: string
  total_rules_checked?: number
  triggers_detected?: number
  actions_triggered?: number
  status?: string
}

export type SignalsResponse = {
  mode: 'live_first' | 'replay_only'
  rules: Signal[]
  events: Signal[]
  forecasts: Signal[]
  pipeline: Signal[]
  upstream_actions: UpstreamAction[]
  check_logs: CheckLog[]
}

export type SourceStatus = {
  mode: 'live_first' | 'replay_only'
  escalation_step: number
  sources: SourceSnapshot[]
}

export type Area = { id: string; name: string; geometry: GeoJSON.Geometry; country?: string; level?: number }

export type SignalKind = 'all' | 'rules' | 'events' | 'forecasts' | 'pipeline'

export type MatcherResult = { candidates: { card_id: string; rationale: string; rank: number }[]; disclaimer: string }
export type ExplainerResult = { summary: string; cited_snapshot_ids: string[]; missing_inputs: string[] }
export type BlockerSuggestion = { code: string; severity: string; summary: string; needs_human_review: boolean }

export type ApprovalVerification = {
  current_digest: string
  three_role_approval_valid: boolean
  signatures: {
    role: Role
    signer: string
    decision: string
    signed_at: string
    digest: string
    signature_valid: boolean
    covers_current_case: boolean
  }[]
}

export type IneligibleCard = { card: string; reason: string }
export type EligibleCard = ActionCard

export type TileSource = {
  layer: string
  catalog_url: string
  tile_url: string
  source_layer: string
  join_property: string
  attribution: string
  min_zoom: number
  max_zoom: number
}

export type RegionalHazard = {
  hazard: string
  stage: string | null
  basis: 'probability' | 'upstream_severity'
  observed: number | string | null
  indicator?: string
  value?: number | null
  threshold_value?: number | null
  policy_version_id: string
}

export type RegionalUnit = {
  area_id: string
  area_name: string
  country: string
  country_name: string
  probability: number
  return_periods: Record<string, number>
  valid_date?: string
  lead_months?: number
  indicator?: string
  hazards: RegionalHazard[]
  stage: string | null
  stage_hazard: string | null
  ndma_phase: string | null
  compound: boolean
  snapshot_id: string
}

export type RegionalEvidence = {
  snapshot_id: string
  sha256: string
  endpoint_url: string
  freshness: Freshness
  retrieved_at: string
}

export type RegionalOverview = {
  mode: 'live_first' | 'replay_only'
  generated_at: string
  issue: { id?: string; season?: string; year?: number; valid_date?: string; lead_months?: number; indicator?: string; data_source?: string }
  available_issues: { id: string; target_season: string; target_year: number; lead_months: number; valid_date: string }[]
  evidence: Record<string, RegionalEvidence>
  policies: Record<string, string>
  totals: {
    units: number; countries: number; activating: number
    ready: number; set: number; go: number; compound: number; max_probability: number
  }
  countries: { country: string; country_name: string; units: number; activating: number; max_probability: number; stages: Record<string, number> }[]
  units: RegionalUnit[]
  tiles: TileSource
}

export type IndicatorRegistry = {
  indicators: {
    code: string; name: string; category?: string | null; data_source?: string | null
    unit?: string | null; description?: string | null
    supports_forecast: boolean; supports_monitoring: boolean; timescale_months?: number | null
  }[]
}
