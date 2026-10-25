import { Await, createFileRoute } from "@tanstack/react-router"
import { TriangleAlertIcon } from "lucide-react"

import { api, type Deal, type Delivery, type Fundamentals } from "@/lib/api"
import { num } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Empty, Loading, PageHeader, Section } from "@/components/common"

export const Route = createFileRoute("/stocks/$symbol")({
  validateSearch: (s: Record<string, unknown>): { sector?: string } => ({
    sector: typeof s.sector === "string" && s.sector ? s.sector : undefined,
  }),
  loaderDeps: ({ search }) => ({ sector: search.sector }),
  loader: async ({ params, deps }) => {
    // fundamentals can take seconds (first NSE fetch of the day): stream it in instead of blocking the page
    const fundamentals = api.fundamentals(params.symbol, deps.sector)
    const [delivery, deals] = await Promise.all([api.delivery(params.symbol, 90), api.deals(params.symbol, 90)])
    return { fundamentals, delivery, deals }
  },
  staleTime: 10 * 60_000,
  component: Stock,
})

function Stock() {
  const { symbol } = Route.useParams()
  const { sector } = Route.useSearch()
  const { fundamentals, delivery, deals } = Route.useLoaderData()
  return (
    <>
      <PageHeader title={symbol} description={sector ?? "NSE"} />
      <div className="space-y-6">
        <Section title="Fundamentals" description="From NSE XBRL filings, cached daily. First load of the day can take a few seconds.">
          <Await promise={fundamentals} fallback={<Loading />}>
            {(f) => <FundamentalsBody f={f} />}
          </Await>
        </Section>
        <div className="grid gap-6 lg:grid-cols-2">
          <DeliverySection rows={delivery} />
          <DealsSection deals={deals} />
        </div>
      </div>
    </>
  )
}

function FundamentalsBody({ f }: { f: Fundamentals }) {
  return (
        <div className="space-y-4">
          {f.red_flags?.length ? (
            <div className="flex flex-wrap gap-2">
              {f.red_flags.map((r) => (
                <Badge key={r} variant="destructive">
                  <TriangleAlertIcon /> {r}
                </Badge>
              ))}
            </div>
          ) : (
            <Badge variant="outline" className="text-positive">
              No red flags
            </Badge>
          )}
          {f.quarters.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Quarter ({f.quarters[0].type.toLowerCase()})</TableHead>
                  <TableHead className="text-right">Revenue (₹ cr)</TableHead>
                  <TableHead className="text-right">Net profit (₹ cr)</TableHead>
                  <TableHead className="text-right">EPS</TableHead>
                  <TableHead className="text-right">Debt / equity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {f.quarters.map((x) => (
                  <TableRow key={x.quarter}>
                    <TableCell>{x.quarter}</TableCell>
                    <TableCell className="text-right tabular-nums">{num(x.revenue_cr, 0)}</TableCell>
                    <TableCell className={cn("text-right tabular-nums", (x.profit_cr ?? 0) < 0 && "text-negative")}>
                      {num(x.profit_cr, 0)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{num(x.eps)}</TableCell>
                    <TableCell className="text-right tabular-nums">{num(x.debt_equity)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <Empty>No quarterly results available.</Empty>
          )}
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
            {f.promoter.length > 0 && (
              <span>
                <span className="text-muted-foreground">Promoter holding: </span>
                {f.promoter.map(([d, p]) => `${d} ${p}%`).join(" · ")}
              </span>
            )}
            {f.pledge_pct != null && (
              <span>
                <span className="text-muted-foreground">Pledged: </span>
                {f.pledge_pct}%
              </span>
            )}
          </div>
        </div>
  )
}

function DeliveryBars({ rows }: { rows: Delivery[] }) {
  const vals = rows.map((r) => r.deliv_per ?? 0)
  const sorted = [...vals].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)] ?? 0
  const max = Math.max(1, ...vals)
  return (
    <div>
      <div className="relative flex h-40 items-end gap-px">
        <div
          className="pointer-events-none absolute inset-x-0 border-t border-dashed border-muted-foreground/50"
          style={{ bottom: `${(median / max) * 100}%` }}
        />
        {rows.map((r) => (
          <Tooltip key={r.date}>
            <TooltipTrigger
              render={
                <div
                  className={cn("min-w-0 flex-1 rounded-t-sm", (r.deliv_per ?? 0) > median ? "bg-chart-2" : "bg-chart-1")}
                  style={{ height: `${((r.deliv_per ?? 0) / max) * 100}%` }}
                />
              }
            />
            <TooltipContent>
              {r.date}: {num(r.deliv_per, 1)}%
            </TooltipContent>
          </Tooltip>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted-foreground">
        <span>{rows[0]?.date}</span>
        <span>dashed: median {num(median, 1)}%</span>
        <span>{rows.at(-1)?.date}</span>
      </div>
    </div>
  )
}

function DeliverySection({ rows }: { rows: Delivery[] }) {
  return (
    <Section title="Delivery %" description="Share of traded volume actually delivered, last 90 days. Darker bars are above the median.">
      {rows.length ? <DeliveryBars rows={rows} /> : <Empty>No delivery data.</Empty>}
    </Section>
  )
}

function DealsSection({ deals }: { deals: Deal[] }) {
  return (
    <Section title="Bulk & block deals" description="Last 90 days.">
      {!deals.length ? (
        <Empty>No bulk or block deals.</Empty>
      ) : (
        <div className="max-h-72 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Side</TableHead>
                <TableHead className="text-right">Value (₹ cr)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {deals.map((x, i) => (
                <TableRow key={i}>
                  <TableCell className="tabular-nums">{x.date}</TableCell>
                  <TableCell className="max-w-56 truncate">{x.client}</TableCell>
                  <TableCell className={x.side === "BUY" ? "text-positive" : "text-negative"}>{x.side}</TableCell>
                  <TableCell className="text-right tabular-nums">{num((x.qty * x.price) / 1e7)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}
