export type GuideArticle = {
  keywords: string[]
  response: string
}

/**
 * Curated product knowledge, sourced from the public README and the in-app
 * workflow. Keeping it local makes every answer inspectable and avoids
 * presenting an unverified language-model response as operational guidance.
 */
export const GUIDE_KNOWLEDGE: GuideArticle[] = [
  {
    keywords: ['approval', 'approvals', 'approve', 'review', 'sign', 'signature', 'co-sign'],
    response: 'Open a decision case and use the Approvals tab. A case moves to review only after its critical readiness tasks are resolved; the required roles then record their approvals against the same evidence digest.',
  },
  {
    keywords: ['evidence', 'source', 'sources', 'data', 'icpac', 'forecast', 'provenance', 'freshness', 'replay', 'synthetic'],
    response: 'Use Sources to inspect the recorded ICPAC inputs and their freshness. In each case, the Evidence tab shows the exact snapshots and provenance used for the assessment. Replay and synthetic evidence are always labelled.',
  },
  {
    keywords: ['case', 'cases', 'readiness', 'action', 'actions', 'stage', 'regional', 'assessment', 'trigger'],
    response: 'Regional Readiness shows the current assessment across the region. Open a row to see its decision case, then use Actions & Readiness to review which pre-agreed actions fit the stage and available lead time.',
  },
  {
    keywords: ['role', 'roles', 'user', 'users', 'permission', 'permissions', 'admin', 'observer', 'login', 'sign-in'],
    response: 'Linda Node uses role-based permissions. The workspace shows role-gated controls with an explanation, while the API remains the enforcer. The demo accounts are fictional and use the documented demo password.',
  },
  {
    keywords: ['export', 'exports', 'packet', 'cap', 'api', 'integration', 'webhook', 'partner', 'husika'],
    response: 'Approved records can be exported as a decision packet, CAP document, Husika-shaped payload, or offline bundle. The partner API is read-only, and Linda Node does not dispatch alerts or call partner write APIs.',
  },
  {
    keywords: ['emergency', 'alert', 'fund', 'funds', 'money', 'advice', 'decision', 'operational'],
    response: 'Linda Node is not an emergency service and does not make operational decisions, dispatch public alerts, move funds, or select beneficiaries. Use the recorded case evidence and your organisation’s approved procedures for real-world action.',
  },
  {
    keywords: ['accessible', 'accessibility', 'screen', 'reader', 'keyboard', 'contrast', 'motion', 'text', 'disability'],
    response: 'Select the accessibility button below to enlarge text, increase contrast, or reduce motion. The workspace also supports keyboard navigation, visible focus states, semantic labels, and screen-reader announcements.',
  },
  {
    keywords: ['what', 'linda', 'purpose', 'overview', 'about', 'platform'],
    response: 'Linda Node turns an evidence-backed readiness signal into a governed decision case. It records the evidence, action readiness, required approvals, exports, and audit trail; it does not issue public alerts or move funds.',
  },
]

const STOP_WORDS = new Set(['about', 'after', 'also', 'and', 'are', 'can', 'does', 'for', 'from', 'have', 'how', 'i', 'in', 'is', 'it', 'me', 'of', 'on', 'please', 'should', 'the', 'this', 'to', 'what', 'where', 'with', 'work'])

function queryTerms(question: string) {
  return question.toLowerCase().match(/[a-z0-9-]+/g)?.filter((word) => word.length > 1 && !STOP_WORDS.has(word)) ?? []
}

export function answerGuideQuestion(question: string): string {
  const terms = queryTerms(question)
  if (!terms.length) return 'Please ask about a Linda Node workflow, such as evidence, cases, approvals, sources, exports, or accessibility.'

  const bestMatch = GUIDE_KNOWLEDGE
    .map((article) => ({ article, score: terms.reduce((total, term) => total + Number(article.keywords.includes(term)), 0) }))
    .sort((left, right) => right.score - left.score)[0]

  if (!bestMatch || bestMatch.score === 0) {
    return 'I can help with Linda Node’s readiness signals, evidence, cases, approvals, actions, sources, roles, exports, and accessibility. For a specific decision, open the relevant case to review its evidence trace and audit record.'
  }
  return bestMatch.article.response
}
