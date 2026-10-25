import type { Headline, Mood } from "@/lib/api"
import { moodLabel, signed } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Section } from "@/components/common"

export function ImpactBadge({ impact }: { impact?: number }) {
  if (impact == null) return <Badge variant="outline">untagged</Badge>
  return (
    <Badge
      variant="outline"
      className={cn("tabular-nums", impact > 0 && "border-positive/40 text-positive", impact < 0 && "border-negative/40 text-negative")}
    >
      {signed(impact, 0)}
    </Badge>
  )
}

export function HeadlineRow({ h }: { h: Headline }) {
  return (
    <li className="flex gap-3 py-2.5">
      <ImpactBadge impact={h.impact} />
      <div className="min-w-0 flex-1">
        {h.link ? (
          <a href={h.link} target="_blank" rel="noreferrer" className="text-sm hover:underline">
            {h.title}
          </a>
        ) : (
          <span className="text-sm">{h.title}</span>
        )}
        <div className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-muted-foreground">
          <span>{h.published}</span>
          {h.category && <span>· {h.category.replace("_", " ")}</span>}
          {h.sectors?.length ? <span>· {h.sectors.join(", ")}</span> : null}
        </div>
      </div>
    </li>
  )
}

/** Market mood from Claude-tagged Mint headlines: overall score, drivers, top headlines either way. */
export function MoodCard({ mood, className }: { mood: Mood | null; className?: string }) {
  if (!mood) {
    return (
      <Section title="Market mood" className={className} description="No tagged news yet (needs ANTHROPIC_API_KEY).">
        <p className="text-sm text-muted-foreground">Run a scan to fetch and tag Mint headlines.</p>
      </Section>
    )
  }
  const label = moodLabel(mood.score)
  const drivers = Object.entries(mood.by_category).sort((a, b) => a[1].net - b[1].net)
  const maxAbs = Math.max(1, ...drivers.map(([, v]) => Math.abs(v.net)))
  return (
    <Section
      title="Market mood"
      className={className}
      description={`${mood.n} market-relevant Mint headlines, last ${mood.days} days. Context only, not a validated signal.`}
      action={
        <div className="text-right">
          <div
            className={cn(
              "text-2xl font-semibold tabular-nums",
              label === "risk-on" && "text-positive",
              label === "risk-off" && "text-negative"
            )}
          >
            {signed(mood.score)}
          </div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      }
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <div>
          <h3 className="mb-2 text-xs font-medium text-muted-foreground">Net impact by driver</h3>
          <ul className="space-y-1.5">
            {drivers.map(([cat, v]) => (
              <li key={cat} className="grid grid-cols-[7rem_1fr_2.5rem] items-center gap-2 text-xs">
                <span className="truncate">{cat.replace("_", " ")}</span>
                <div className="relative h-2 rounded bg-muted">
                  <div
                    className={cn("absolute top-0 h-2 rounded", v.net >= 0 ? "left-1/2 bg-positive" : "right-1/2 bg-negative")}
                    style={{ width: `${(Math.abs(v.net) / maxAbs) * 50}%` }}
                  />
                </div>
                <span className="text-right tabular-nums text-muted-foreground">
                  {signed(v.net, 0)} <span className="opacity-60">/{v.n}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="text-xs font-medium text-muted-foreground">Most negative</h3>
            <ul className="divide-y">{mood.negative.map((h) => <HeadlineRow key={h.title} h={h} />)}</ul>
          </div>
          <div>
            <h3 className="text-xs font-medium text-muted-foreground">Most positive</h3>
            <ul className="divide-y">{mood.positive.map((h) => <HeadlineRow key={h.title} h={h} />)}</ul>
          </div>
        </div>
      </div>
    </Section>
  )
}
