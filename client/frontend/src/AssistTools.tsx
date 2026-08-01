import { FormEvent, useEffect, useRef, useState } from 'react'
import AccessibilityNew from '@mui/icons-material/AccessibilityNew'
import ChatBubbleOutline from '@mui/icons-material/ChatBubbleOutline'
import Close from '@mui/icons-material/Close'
import Send from '@mui/icons-material/Send'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import Fab from '@mui/material/Fab'
import FormControlLabel from '@mui/material/FormControlLabel'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Switch from '@mui/material/Switch'
import TextField from '@mui/material/TextField'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'

type AccessibilityPreference = 'large-text' | 'high-contrast' | 'reduce-motion'

type ChatMessage = { from: 'assistant' | 'user'; text: string }

const WELCOME: ChatMessage = {
  from: 'assistant',
  text: 'Hi, I’m Linda Guide. Ask about readiness, cases, evidence, approvals, sources, or how to use this workspace.',
}

const QUICK_QUESTIONS = [
  'What does Linda Node do?',
  'How do approvals work?',
  'What data is used?',
]

/** A transparent, local guide: it never fabricates operational guidance. */
export function answerGuideQuestion(question: string): string {
  const text = question.trim().toLowerCase()
  if (!text) return 'Please enter a question and I’ll point you to the relevant part of Linda Node.'
  if (/(approve|approval|sign|review)/.test(text)) {
    return 'Open a decision case and use the Approvals tab. A case moves to review only after its critical readiness tasks are resolved; the required roles then record their approvals against the same evidence digest.'
  }
  if (/(data|source|evidence|icpac|forecast)/.test(text)) {
    return 'Use Sources to inspect the recorded ICPAC inputs and their freshness. In each case, the Evidence tab shows the exact snapshots and provenance used for the assessment. Replay and synthetic evidence are always labelled.'
  }
  if (/(case|readiness|action|stage)/.test(text)) {
    return 'Regional Readiness shows the current assessment across the region. Open a row to see its decision case, then use Actions & Readiness to review which pre-agreed actions fit the stage and available lead time.'
  }
  if (/(accessib|screen reader|keyboard|contrast|motion|text size)/.test(text)) {
    return 'Select the accessibility button below to enlarge text, increase contrast, or reduce motion. The workspace is also designed for keyboard navigation and screen readers.'
  }
  if (/(what.*linda|what.*this|how.*work|purpose)/.test(text)) {
    return 'Linda Node turns an evidence-backed readiness signal into a governed decision case. It records the evidence, action readiness, required approvals, exports, and audit trail; it does not issue public alerts or move funds.'
  }
  return 'I can help with how Linda Node uses readiness signals, evidence, cases, approvals, actions, sources, and accessibility. For a specific decision, open the relevant case so you can review its evidence trace and audit record.'
}

function preferenceKey(preference: AccessibilityPreference) {
  return `linda-${preference}`
}

function applyPreference(preference: AccessibilityPreference, enabled: boolean) {
  document.documentElement.classList.toggle(preference, enabled)
  localStorage.setItem(preferenceKey(preference), String(enabled))
}

function AccessibilityControls() {
  const [open, setOpen] = useState(false)
  const [preferences, setPreferences] = useState<Record<AccessibilityPreference, boolean>>(() => ({
    'large-text': localStorage.getItem(preferenceKey('large-text')) === 'true',
    'high-contrast': localStorage.getItem(preferenceKey('high-contrast')) === 'true',
    'reduce-motion': localStorage.getItem(preferenceKey('reduce-motion')) === 'true',
  }))

  useEffect(() => {
    for (const [preference, enabled] of Object.entries(preferences) as [AccessibilityPreference, boolean][]) {
      applyPreference(preference, enabled)
    }
  }, [preferences])

  const setPreference = (preference: AccessibilityPreference, enabled: boolean) => {
    setPreferences((current) => ({ ...current, [preference]: enabled }))
  }

  return (
    <>
      <Tooltip title="Accessibility options" placement="left">
        <Fab color="secondary" size="medium" onClick={() => setOpen(true)} aria-label="Open accessibility options">
          <AccessibilityNew />
        </Fab>
      </Tooltip>
      <Dialog open={open} onClose={() => setOpen(false)} aria-labelledby="accessibility-title">
        <DialogTitle id="accessibility-title">Accessibility options</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary" sx={{ mb: 1.5 }}>
            Choose the display settings that make Linda Node easier for you to use. Your choices are saved on this device.
          </Typography>
          <Stack>
            <FormControlLabel control={<Switch checked={preferences['large-text']} onChange={(event) => setPreference('large-text', event.target.checked)} />} label="Larger text" />
            <FormControlLabel control={<Switch checked={preferences['high-contrast']} onChange={(event) => setPreference('high-contrast', event.target.checked)} />} label="Higher contrast" />
            <FormControlLabel control={<Switch checked={preferences['reduce-motion']} onChange={(event) => setPreference('reduce-motion', event.target.checked)} />} label="Reduce motion" />
          </Stack>
        </DialogContent>
        <DialogActions><Button onClick={() => setOpen(false)}>Done</Button></DialogActions>
      </Dialog>
    </>
  )
}

function Chatbot() {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME])
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) window.setTimeout(() => inputRef.current?.focus(), 0)
  }, [open])

  const ask = (value: string) => {
    const trimmed = value.trim()
    if (!trimmed) return
    setMessages((current) => [...current, { from: 'user', text: trimmed }, { from: 'assistant', text: answerGuideQuestion(trimmed) }])
    setQuestion('')
  }
  const submit = (event: FormEvent) => { event.preventDefault(); ask(question) }

  return (
    <>
      <Tooltip title="Ask Linda Guide" placement="left">
        <Fab color="primary" size="medium" onClick={() => setOpen(true)} aria-label="Open Linda Guide">
          <ChatBubbleOutline />
        </Fab>
      </Tooltip>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm" aria-labelledby="linda-guide-title">
        <DialogTitle id="linda-guide-title" sx={{ pr: 7 }}>
          Linda Guide
          <IconButton onClick={() => setOpen(false)} aria-label="Close Linda Guide" sx={{ position: 'absolute', right: 12, top: 10 }}><Close /></IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1.25} aria-live="polite" aria-label="Linda Guide conversation">
            {messages.map((message, index) => (
              <Paper key={`${message.from}-${index}`} variant="outlined" sx={{ p: 1.25, alignSelf: message.from === 'user' ? 'flex-end' : 'flex-start', maxWidth: '92%', bgcolor: message.from === 'user' ? 'primary.main' : 'background.paper', color: message.from === 'user' ? 'primary.contrastText' : 'text.primary' }}>
                <Typography variant="body2">{message.text}</Typography>
              </Paper>
            ))}
          </Stack>
          {messages.length === 1 && (
            <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 2 }}>
              {QUICK_QUESTIONS.map((item) => <Button key={item} variant="outlined" onClick={() => ask(item)}>{item}</Button>)}
            </Stack>
          )}
          <Alert severity="info" sx={{ mt: 2 }}>Linda Guide provides workspace help, not emergency advice or operational decisions.</Alert>
        </DialogContent>
        <Box component="form" onSubmit={submit} sx={{ display: 'flex', gap: 1, p: 2 }}>
          <TextField inputRef={inputRef} fullWidth label="Ask a question" value={question} onChange={(event) => setQuestion(event.target.value)} />
          <IconButton color="primary" type="submit" disabled={!question.trim()} aria-label="Send question"><Send /></IconButton>
        </Box>
      </Dialog>
    </>
  )
}

export function AssistTools() {
  return (
    <Box sx={{ position: 'fixed', right: { xs: 16, sm: 24 }, bottom: { xs: 16, sm: 24 }, zIndex: (theme) => theme.zIndex.modal - 1 }}>
      <Stack spacing={1} alignItems="flex-end">
        <AccessibilityControls />
        <Chatbot />
      </Stack>
    </Box>
  )
}
