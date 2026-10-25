import { createFileRoute, useNavigate } from "@tanstack/react-router"

import { api } from "@/lib/api"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Empty, PageHeader, Section } from "@/components/common"
import { HeadlineRow, MoodCard } from "@/components/mood"

const CATEGORIES = ["geopolitics", "rbi_rates", "govt_policy", "macro_data", "global_markets", "commodities", "fii_flows", "sector", "company", "other"]
const DAYS = [1, 3, 7, 14, 30]

type Search = { days: number; category?: string }

export const Route = createFileRoute("/news")({
  validateSearch: (s: Record<string, unknown>): Search => ({
    days: DAYS.includes(Number(s.days)) ? Number(s.days) : 3,
    category: CATEGORIES.includes(String(s.category)) ? String(s.category) : undefined,
  }),
  loaderDeps: ({ search }) => search,
  loader: async ({ deps }) => {
    const [mood, news] = await Promise.all([api.mood(deps.days), api.news(deps.days, deps.category)])
    return { mood, news }
  },
  staleTime: 5 * 60_000,
  component: News,
})

function News() {
  const { days, category } = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const { mood, news } = Route.useLoaderData()
  return (
    <>
      <PageHeader
        title="News"
        description="Mint headlines, tagged by Claude for driver and market impact (−2 to +2). Archived on every scan."
        actions={
          <div className="flex gap-2">
            <Select value={days} onValueChange={(v) => v != null && navigate({ search: (s) => ({ ...s, days: v }) })}>
              <SelectTrigger className="w-32">
                <SelectValue>{(v: number) => `Last ${v} day${v > 1 ? "s" : ""}`}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {DAYS.map((d) => (
                  <SelectItem key={d} value={d}>
                    Last {d} day{d > 1 ? "s" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={category ?? null}
              onValueChange={(v) => navigate({ search: (s) => ({ ...s, category: v ?? undefined }) })}
            >
              <SelectTrigger className="w-44">
                <SelectValue placeholder="All categories">{(v: string | null) => (v ? v.replace("_", " ") : "All categories")}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={null}>All categories</SelectItem>
                {CATEGORIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c.replace("_", " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />
      <div className="space-y-6">
        <MoodCard mood={mood} />
        <Section title="Headlines" description={`${news.length} headlines`}>
          {!news.length ? (
            <Empty>No headlines for this period.</Empty>
          ) : (
            <ul className="divide-y">
              {news.map((h) => (
                <HeadlineRow key={h.link ?? h.title} h={h} />
              ))}
            </ul>
          )}
        </Section>
      </div>
    </>
  )
}
