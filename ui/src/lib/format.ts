import { cn } from "@/lib/utils"

export const pct = (x: number | null | undefined, digits = 1) => (x == null ? "–" : `${(x * 100).toFixed(digits)}%`)

export const num = (x: number | null | undefined, digits = 2) =>
  x == null ? "–" : x.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits })

export const rupees = (x: number | null | undefined, digits = 1) => (x == null ? "–" : `₹${num(x, digits)}`)

export const signed = (x: number | null | undefined, digits = 2) =>
  x == null ? "–" : `${x > 0 ? "+" : ""}${x.toFixed(digits)}`

// R multiples: positive is the trader's edge, negative a loss
export const rClass = (x: number | null | undefined) =>
  cn("tabular-nums", x == null ? "text-muted-foreground" : x > 0 ? "text-positive" : x < 0 ? "text-negative" : "")

export function moodLabel(score: number) {
  return score <= -0.3 ? "risk-off" : score >= 0.3 ? "risk-on" : "mixed"
}

export const timeAgo = (ts: string | null) => {
  if (!ts) return "never"
  const mins = Math.round((Date.now() - new Date(ts.replace(" ", "T")).getTime()) / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const h = Math.round(mins / 60)
  return h < 48 ? `${h}h ago` : `${Math.round(h / 24)}d ago`
}
