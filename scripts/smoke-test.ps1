$ErrorActionPreference = "Stop"

$base = "http://127.0.0.1:8000"

function Invoke-Linda($Method, $Path, $User = "david.drm@demo") {
  Invoke-RestMethod -Method $Method -Uri "$base$Path" -Headers @{ "X-Demo-User" = $User }
}

$health = Invoke-Linda Get "/api/healthz"
if ($health.status -ne "ok") {
  throw "Health check failed"
}

Invoke-Linda Post "/api/seed" | Out-Null
$case = (Invoke-Linda Get "/api/cases").cases[0]

try {
  Invoke-Linda Post "/api/cases/$($case.id)/send-review" | Out-Null
  throw "Blocked case advanced unexpectedly"
} catch {
  if ($_.Exception.Message -notmatch "422") {
    throw
  }
}

Invoke-Linda Post "/api/cases/$($case.id)/tasks/task_transport/resolve" "david.drm@demo" | Out-Null
Invoke-Linda Post "/api/cases/$($case.id)/send-review" "david.drm@demo" | Out-Null
Invoke-Linda Post "/api/cases/$($case.id)/approve" "amina.ews@demo" | Out-Null
Invoke-Linda Post "/api/cases/$($case.id)/approve" "david.drm@demo" | Out-Null
$approved = Invoke-Linda Post "/api/cases/$($case.id)/approve" "grace.ngo@demo"

foreach ($kind in "packet", "cap", "husika", "bundle") {
  Invoke-Linda Post "/api/cases/$($case.id)/exports/$kind" | Out-Null
}

$audit = Invoke-Linda Get "/api/cases/$($case.id)/audit"
$verify = Invoke-Linda Get "/api/cases/$($case.id)/verify-signatures"
$adminHeaders = @{ "X-Demo-User" = "admin@demo" }
$integrationKey = Invoke-RestMethod -Method Post -Uri "$base/api/admin/integration-keys" -Headers $adminHeaders -ContentType "application/json" -Body '{"label":"smoke-test"}'
$integration = Invoke-RestMethod -Method Get -Uri "$base/integration/v1/activations/$($case.id)/verify" -Headers @{ Authorization = "Bearer $($integrationKey.key)" }

if ($approved.state -ne "APPROVED") {
  throw "Case did not approve"
}
if ($approved.approvals.Count -ne 3) {
  throw "Expected 3 approvals"
}
if (-not $audit.chain.ok) {
  throw "Audit chain failed"
}
if (-not $verify.ok) {
  throw "Signature verification failed"
}
if (-not $integration.chain.ok) {
  throw "Integration verification failed"
}

[pscustomobject]@{
  health = $health.status
  case_state = $approved.state
  approvals = $approved.approvals.Count
  audit_chain = $audit.chain.ok
  signatures = $verify.ok
  integration_verify = $integration.chain.ok
  events = $audit.chain.events
}
