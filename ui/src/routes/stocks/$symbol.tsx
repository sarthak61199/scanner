import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { TriangleAlertIcon } from "lucide-react"

import { q, type Delivery } from "@/lib/api"
import { num } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Empty, ErrorState, Loading, PageHeader, Section } from "@/components/common"

export const Route = createFileRoute("/stocks/$symbol")({
  validateSearch: (s: Record<string, unknown>): { sector?: string } => ({
    sector: typeof s.sector === "string" && s.sector ? s.sector : undefined,
  }),
  component: Stock,
})

function Stock() {
  const { symbol } = Route.useParams()
  const { sector } = Route.useSearch()
  return (
    <>
      <PageHeader title={symbol} description={sector ?? "NSE"} />
      <div className="space-y-6">
        <FundamentalsSection symbol={symbol} sector={sector} />
        <div className="grid gap-6 lg:grid-cols-2">
          <DeliverySection symbol={symbol} />
          <DealsSection symbol={symbol} />
        </div>
      </div>
    </>
  )
}

function FundamentalsSection({ symbol, sector }: { symbol: string; sector?: string }) {
  const f = useQuery(q.fundamentals(symbol, sector))
  return (
    <Section title="Fundamentals" description="From NSE XBRL filings, cached daily. First load of the day can take a few seconds.">
      {f.isPending ? (
        <Loading />
      ) : f.error ? (
        <ErrorState error={f.error} />
      ) : (
        <div className="space-y-4">
          {f.data.red_flags?.length ? (
            <div className="flex flex-wrap gap-2">
              {f.data.red_flags.map((r) => (
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
          {f.data.quarters.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Quarter ({f.data.quarters[0].type.toLowerCase()})</TableHead>
                  <TableHead className="text-right">Revenue (₹ cr)</TableHead>
                  <TableHead className="text-right">Net profit (₹ cr)</TableHead>
                  <TableHead className="text-right">EPS</TableHead>
                  <TableHead className="text-right">Debt / equity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {f.data.quarters.map((x) => (
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
            {f.data.promoter.length > 0 && (
              <span>
                <span className="text-muted-foreground">Promoter holding: </span>
                {f.data.promoter.map(([d, p]) => `${d} ${p}%`).join(" · ")}
              </span>
            )}
            {f.data.pledge_pct != null && (
              <span>
                <span className="text-muted-foreground">Pledged: </span>
                {f.data.pledge_pct}%
              </span>
            )}
          </div>
        </div>
      )}
    </Section>
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

function DeliverySection({ symbol }: { symbol: string }) {
  const d = useQuery(q.delivery(symbol, 90))
  return (
    <Section title="Delivery %" description="Share of traded volume actually delivered, last 90 days. Darker bars are above the median.">
      {d.isPending ? <Loading /> : d.error ? <ErrorState error={d.error} /> : d.data.length ? <DeliveryBars rows={d.data} /> : <Empty>No delivery data.</Empty>}
    </Section>
  )
}

function DealsSection({ symbol }: { symbol: string }) {
  const d = useQuery(q.deals(symbol, 90))
  return (
    <Section title="Bulk & block deals" description="Last 90 days.">
      {d.isPending ? (
        <Loading />
      ) : d.error ? (
        <ErrorState error={d.error} />
      ) : !d.data.length ? (
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
              {d.data.map((x, i) => (
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
