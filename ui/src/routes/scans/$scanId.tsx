import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { q } from "@/lib/api"
import { num, rClass, signed } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Empty, ErrorState, Loading, PageHeader, Section } from "@/components/common"
import { ScanView, StockLink } from "@/components/scan-view"

export const Route = createFileRoute("/scans/$scanId")({
  component: ScanPage,
})

function ScanPage() {
  const id = Number(Route.useParams().scanId)
  const scan = useQuery(q.scan(id))
  return (
    <>
      <PageHeader title={`Scan #${id}`} description={scan.data?.created} />
      {scan.isPending ? (
        <Loading rows={6} />
      ) : scan.error ? (
        <ErrorState error={scan.error} />
      ) : (
        <div className="space-y-6">
          <ScanView scan={scan.data} />
          <Trades scanId={id} />
        </div>
      )}
    </>
  )
}

/** Every backtest trade of the validated setups at the time of this scan. */
function Trades({ scanId }: { scanId: number }) {
  const validated = useQuery(q.validated())
  const setups = validated.data?.setups.map((s) => [s.setup, ...s.filters].join("+")) ?? []
  const [setup, setSetup] = useState<string | null>(null)
  const [symbol, setSymbol] = useState("")
  const trades = useQuery(q.trades(scanId, setup ?? undefined, symbol.trim() || undefined))
  const rows = trades.data ?? []
  const avg = rows.length ? rows.reduce((a, t) => a + t.R, 0) / rows.length : null
  return (
    <Section
      title="Backtest trades"
      description={
        trades.data
          ? `${rows.length} trades · avg ${signed(avg, 3)}R after costs · ${rows.length ? Math.round((100 * rows.filter((t) => t.R > 0).length) / rows.length) : 0}% profitable`
          : "Every historical signal of the validated setups."
      }
      action={
        <div className="flex gap-2">
          <Select value={setup} onValueChange={(v) => setSetup(v)}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="All setups" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={null}>All setups</SelectItem>
              {setups.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input className="w-32" placeholder="Symbol" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} />
        </div>
      }
    >
      {trades.isPending ? (
        <Loading />
      ) : trades.error ? (
        <ErrorState error={trades.error} />
      ) : !rows.length ? (
        <Empty>No trades match.</Empty>
      ) : (
        <div className="max-h-[32rem] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-card">
              <TableRow>
                <TableHead>Stock</TableHead>
                <TableHead>Setup</TableHead>
                <TableHead>Entry date</TableHead>
                <TableHead className="text-right">Entry</TableHead>
                <TableHead className="text-right">Exit</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead className="text-right">Days</TableHead>
                <TableHead className="text-right">R</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...rows].reverse().slice(0, 500).map((t, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <StockLink symbol={t.symbol} sector={t.sector} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{t.variant}</TableCell>
                  <TableCell className="tabular-nums">{t.date}</TableCell>
                  <TableCell className="text-right tabular-nums">{num(t.entry)}</TableCell>
                  <TableCell className="text-right tabular-nums">{num(t.exit)}</TableCell>
                  <TableCell className="text-xs">{t.reason}</TableCell>
                  <TableCell className="text-right tabular-nums">{t.days}</TableCell>
                  <TableCell className={cn("text-right", rClass(t.R))}>{signed(t.R)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {rows.length > 500 && <p className="p-2 text-xs text-muted-foreground">Showing the newest 500 of {rows.length}.</p>}
        </div>
      )}
    </Section>
  )
}
