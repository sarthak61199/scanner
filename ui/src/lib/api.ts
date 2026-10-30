// Same origin: FastAPI serves this UI and the API under /api (Vite proxies it in dev).
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init?.headers },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === "string" ? body.detail : res.statusText
    throw new ApiError(res.status, detail)
  }
  return res.json()
}

// ---------- types (mirror api.py responses) ----------
export type JobKind = "scan" | "research"
export type JobStatus = "queued" | "running" | "done" | "failed"

export type Job = {
  id: number
  kind: JobKind
  status: JobStatus
  trigger?: "manual" | "schedule"
  created: string
  started: string | null
  finished: string | null
  error: string | null
  log?: string
}

export type Health = {
  ok: boolean
  rows: Record<string, number>
  last_scan: string | null
  active_job: number | null
}

export type Sector = {
  sector: string
  ret63: number | null
  ret126: number | null
  breadth: number | null
  n: number
  score: number | null
}

export type Plan = {
  symbol: string
  sector: string
  setup: string
  score: number
  entry: number
  stop: number
  target: number | "trail"
  exit: string
  qty: number
  test_avgR: number | null
  slot_test_avgR: number | null
  conviction?: string
  note: string | null
}

export type WatchItem = { sym: string; sector: string; score: number; close: number }
export type Rejected = { symbol: string; setup: string; red_flags: string }

export type Headline = {
  link?: string
  published: string
  feed: string
  title: string
  summary: string
  category?: string
  impact?: number
  sectors?: string[]
}

export type Mood = {
  days: number
  n: number
  score: number
  by_category: Record<string, { n: number; net: number }>
  by_sector: Record<string, { n: number; net: number }>
  negative: Headline[]
  positive: Headline[]
}

export type Quarter = {
  quarter: string
  type: string
  revenue_cr: number | null
  profit_cr: number | null
  eps: number | null
  debt_equity: number | null
}

export type Fundamentals = {
  date: string
  symbol: string
  quarters: Quarter[]
  promoter: [string, number][]
  pledge_pct: number | null
  red_flags?: string[]
}

export type ScanSummary = {
  id: number
  job_id: number | null
  created: string
  n_plans: number
  symbols: string[]
  mood_score: number | null
}

export type Scan = {
  id: number
  job_id: number | null
  created: string
  sectors: Sector[]
  plans: Plan[]
  watchlist: WatchItem[]
  rejected: Rejected[]
  funds: Record<string, Fundamentals>
  mood: Mood | null
}

export type Trade = {
  scan_id: number
  symbol: string
  setup: string
  variant: string
  mom: number | null
  date: string
  exit_date: string
  entry: number
  exit: number
  reason: string
  days: number
  gross_R: number
  R: number
  sector: string
}

export type PartStats = {
  n: number
  avg_r: number | null
  win: number | null
  taken: number
  taken_avg_r: number | null
  max_dd_r: number | null
}

export type ResearchRow = {
  setup: string
  filters: string[]
  exit: string
  stop_atr: number
  train: PartStats
  test: PartStats
  train_ex_best_year: number | null
  by_year: Record<string, { n: number; avg_r: number }>
  fails: string[]
}

export type Validated = {
  generated: string
  test_start: string
  rules: Record<string, number>
  setups: Omit<ResearchRow, "fails">[]
  age_days?: number
}

export type ResearchRun = {
  id: number
  job_id: number | null
  created: string
  test_start: string
  rows: ResearchRow[] | null
  validated: Validated
}

export type Config = {
  capital: number
  risk_pct: number
  max_open: number
  min_turnover_cr: number
  top: number
  history_years: number
  test_months: number
  cost_pct: number
  setups: string[]
  filters: string[]
  exits: string[]
  stop_widths: number[]
  macro: Record<string, number>
  mood_days: number
  exit_rules: Record<string, string>
}

export type Delivery = { date: string; deliv_per: number | null }
export type Deal = {
  date: string
  kind: string
  symbol: string
  client: string
  side: string
  qty: number
  price: number
}

export type PaperTrade = {
  id: number
  scan_id: number
  symbol: string
  sector: string
  variant: string
  setup: string
  filters: string[]
  exit_rule: string
  stop_atr: number
  signal_date: string
  entry: number
  initial_stop: number
  qty: number
  score: number
  conviction: "HIGH" | "MEDIUM" | "LOW" | null
  note: string | null
  rejected: string | null
  taken: boolean
  status: "open" | "closed"
  current_stop: number | null
  last_close: number | null
  exit_date: string | null
  exit: number | null
  reason: string | null
  days: number
  gross_R: number
  R: number
  updated: string
  backtest_slot_r: number | null
}

export type JournalGroup = {
  n: number
  closed: number
  open: number
  avg_r: number | null
  low: number | null
  high: number | null
  win: number | null
  total_r: number
}

export type GoLive = {
  ready: boolean
  start: string
  checks: { key: string; label: string; value: number | null; target: string; ok: boolean }[]
  avg_r: number | null
  low: number | null
  high: number | null
  expected_r: number | null
}

export type JournalStats = {
  go_live: GoLive
  overall: { accepted: JournalGroup; taken: JournalGroup; rejected: JournalGroup }
  by_setup: {
    variant: string
    validated: boolean
    all: JournalGroup
    taken: JournalGroup
    backtest_test_avg_r: number | null
    backtest_slot_avg_r: number | null
  }[]
  by_conviction: Record<"HIGH" | "MEDIUM" | "LOW" | "none", JournalGroup>
}

export type Schedule = {
  enabled: boolean
  scan_time: string
  research_day: number
  research_time: string
  research_max_age: number
  next_scan: string
  next_research: string
  last_scheduled: Pick<Job, "id" | "kind" | "status" | "created">[]
}

// ---------- calls ----------
/** null instead of an error when the resource doesn't exist yet (no scan / research run so far). */
async function orNull<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return null
    throw e
  }
}

const qs = (params: Record<string, string | number | undefined>) => {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") p.set(k, String(v))
  const s = p.toString()
  return s ? `?${s}` : ""
}

export const isActive = (j?: Pick<Job, "status">) => j?.status === "queued" || j?.status === "running"

export const api = {
  startJob: (kind: JobKind) => request<Job>("/jobs", { method: "POST", body: JSON.stringify({ kind }) }),
  health: () => request<Health>("/health"),
  config: () => request<Config>("/config"),
  schedule: () => request<Schedule>("/schedule"),
  jobs: () => request<Job[]>("/jobs?limit=50"),
  job: (id: number) => request<Job>(`/jobs/${id}`),
  scans: () => request<ScanSummary[]>("/scans?limit=100"),
  scan: (id: number | "latest") => orNull(request<Scan>(`/scans/${id}`)),
  trades: (scanId: number, setup?: string, symbol?: string) =>
    request<Trade[]>(`/scans/${scanId}/trades${qs({ setup, symbol })}`),
  validated: () => orNull(request<Validated>("/setups/validated")),
  research: (id: number | "latest") => orNull(request<ResearchRun>(`/research/${id}`)),
  news: (days: number, category?: string) => request<Headline[]>(`/news${qs({ days, category })}`),
  mood: (days: number) => request<Mood | null>(`/news/mood?days=${days}`),
  journal: () => request<PaperTrade[]>("/journal"),
  journalStats: () => request<JournalStats>("/journal/stats"),
  fundamentals: (symbol: string, sector = "") => request<Fundamentals>(`/stocks/${symbol}/fundamentals${qs({ sector })}`),
  delivery: (symbol: string, days = 90) => request<Delivery[]>(`/stocks/${symbol}/delivery?days=${days}`),
  deals: (symbol: string, days = 90) => request<Deal[]>(`/stocks/${symbol}/deals?days=${days}`),
}
