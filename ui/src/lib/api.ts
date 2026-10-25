import { queryOptions } from "@tanstack/react-query"

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

// ---------- calls ----------
export const api = {
  startJob: (kind: JobKind) => request<Job>("/jobs", { method: "POST", body: JSON.stringify({ kind }) }),
}

const isActive = (j?: Job) => j?.status === "queued" || j?.status === "running"

export const q = {
  health: () => queryOptions({ queryKey: ["health"], queryFn: () => request<Health>("/health") }),
  config: () => queryOptions({ queryKey: ["config"], queryFn: () => request<Config>("/config"), staleTime: Infinity }),
  jobs: () =>
    queryOptions({
      queryKey: ["jobs"],
      queryFn: () => request<Job[]>("/jobs?limit=50"),
      refetchInterval: (query) => (query.state.data?.some(isActive) ? 3000 : false),
    }),
  job: (id: number) =>
    queryOptions({
      queryKey: ["jobs", id],
      queryFn: () => request<Job>(`/jobs/${id}`),
      refetchInterval: (query) => (isActive(query.state.data) ? 2000 : false),
    }),
  scans: () => queryOptions({ queryKey: ["scans"], queryFn: () => request<ScanSummary[]>("/scans?limit=100") }),
  scan: (id: number | "latest") => queryOptions({ queryKey: ["scans", id], queryFn: () => request<Scan>(`/scans/${id}`) }),
  trades: (scanId: number, setup?: string, symbol?: string) => {
    const p = new URLSearchParams()
    if (setup) p.set("setup", setup)
    if (symbol) p.set("symbol", symbol)
    return queryOptions({
      queryKey: ["scans", scanId, "trades", setup, symbol],
      queryFn: () => request<Trade[]>(`/scans/${scanId}/trades?${p}`),
    })
  },
  validated: () => queryOptions({ queryKey: ["validated"], queryFn: () => request<Validated>("/setups/validated") }),
  research: (id: number | "latest") =>
    queryOptions({ queryKey: ["research", id], queryFn: () => request<ResearchRun>(`/research/${id}`) }),
  news: (days: number, category?: string) =>
    queryOptions({
      queryKey: ["news", days, category],
      queryFn: () => request<Headline[]>(`/news?days=${days}${category ? `&category=${category}` : ""}`),
    }),
  mood: (days: number) => queryOptions({ queryKey: ["mood", days], queryFn: () => request<Mood | null>(`/news/mood?days=${days}`) }),
  fundamentals: (symbol: string, sector = "") =>
    queryOptions({
      queryKey: ["fundamentals", symbol, sector],
      queryFn: () => request<Fundamentals>(`/stocks/${symbol}/fundamentals?sector=${encodeURIComponent(sector)}`),
      staleTime: 60 * 60 * 1000,
    }),
  delivery: (symbol: string, days = 90) =>
    queryOptions({ queryKey: ["delivery", symbol, days], queryFn: () => request<Delivery[]>(`/stocks/${symbol}/delivery?days=${days}`) }),
  deals: (symbol: string, days = 90) =>
    queryOptions({ queryKey: ["deals", symbol, days], queryFn: () => request<Deal[]>(`/stocks/${symbol}/deals?days=${days}`) }),
}
