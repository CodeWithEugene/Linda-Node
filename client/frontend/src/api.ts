export type Role = 'ews_specialist' | 'county_drm_officer' | 'ngo_finance_lead' | 'observer' | 'admin'
export type User = { id: string; email: string; display_name: string; role: Role; org: string }
export type Task = { id: string; action_card_id: string; title: string; owner_role: Role; owner_user_id?: string; criticality: 'critical' | 'normal'; state: string; blocker_code?: string; blocker_note?: string; updated_at: string }
export type Approval = { id: string; role: Role; user_id: string; decision: string; comment?: string; signed_digest: string; signature: string; signed_at: string; superseded: number; display_name: string; org: string }
export type ActionCard = { id: string; hazard: string; title: string; description: string; owner_role: Role; lead_time_days: number; stage_required: string; budget: { currency: string; readiness_tranche: { amount: number; released_at_stage: string }; action_tranche: { amount: number; released_at_stage: string } }; prerequisites: { id: string; title: string; criticality: string }[]; disclaimer: string; raw: string; version_hash: string }
export type ExportRecord = { id: string; kind: string; sha256: string; generated_at: string; meta?: Record<string, unknown> }
export type DecisionCase = { id: string; area_id: string; area_name: string; hazard: string; title: string; state: string; stage?: string; version: number; policy_version_id: string; assessment: { ndma_phase?: string; gates?: { id: string; passed: boolean; detail: string }[]; stage_trace?: { stage: string; condition: string; observed: number; passed: boolean }[]; compound_signals?: string[]; eligible_action_cards?: string[]; ineligible?: { card: string; reason: string }[]; cost_loss?: Record<string, unknown> }; evidence: { id: string; kind: string; label: string; endpoint_url: string; payload_sha256: string; freshness: string }[]; action_cards: ActionCard[]; tasks: Task[]; approvals: Approval[]; exports: ExportRecord[]; created_at: string; updated_at: string }

type ApiError = { error?: { message?: string; detail?: unknown } }

const apiOrigin = (import.meta.env.VITE_LINDA_API_ORIGIN || '').trim().replace(/\/+$/, '')

function apiUrl(path: string): string {
  return apiOrigin ? `${apiOrigin}${path}` : path
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 12_000)
  const abortFromCaller = () => controller.abort()
  init.signal?.addEventListener('abort', abortFromCaller, { once: true })

  let response: Response
  try {
    response = await fetch(apiUrl(path), {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
      ...init,
      signal: controller.signal,
    })
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error('The Linda API did not respond. Check the API deployment and try again.')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
    init.signal?.removeEventListener('abort', abortFromCaller)
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as ApiError
    throw new Error(error.error?.message || (typeof error.error?.detail === 'string' ? error.error.detail : `Request failed (${response.status})`))
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const post = <T>(path: string, body?: unknown) => api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
export const del = <T>(path: string) => api<T>(path, { method: 'DELETE' })
