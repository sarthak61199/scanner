import { useState } from "react"
import { createFileRoute, getRouteApi, notFound, useNavigate } from "@tanstack/react-router"

import { api } from "@/lib/api"
import { num, rClass, signed } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Empty, PageHeader, Section } from "@/components/common"
import { ScanView, StockLink } from "@/components/scan-view"

type Search = { setup?: string; symbol?: string }

export const Route = createFileRoute("/scans/$scanId")({
  validateSearch: (s: Record<string, unknown>): Search => ({
    setup: typeof s.setup === "string" && s.setup ? s.setup : undefined,
    symbol: typeof s.symbol === "string" && s.symbol ? s.symbol.toUpperCase() : undefined,
  }),
  loaderDeps: ({ search }) => search,
  loader: async ({ params, deps }) => {
    const id = Number(params.scanId)
    const [scan, trades] = await Promise.all([api.scan(id), api.trades(id, deps.setup, deps.symbol)])
    if (!scan) throw notFound()
    return { scan, trades }
  },
  staleTime: 5 * 60_000, // a saved scan never changes
  gcTime: 10 * 60_000,
  component: ScanPage,
})

function ScanPage() {
  const { scan } = Route.useLoaderData()
  return (
    <>
      <PageHeader title={`Scan #${scan.id}`} description={scan.created} />
      <div className="space-y-6">
        <ScanView scan={scan} />
        <Trades />
      </div>
    </>
  )
}

const root = getRouteApi("__root__")

/** Every backtest trade of the validated setups at the time of this scan; filters live in the URL. */
function Trades() {
  const { trades } = Route.useLoaderData()
  const { setup, symbol } = Route.useSearch()
  const { validated } = root.useLoaderData()
  const navigate = useNavigate({ from: Route.fullPath })
  const [typed, setTyped] = useState(symbol ?? "")
  const setups = validated?.setups.map((s) => [s.setup, ...s.filters].join("+")) ?? []
  const avg = trades.length ? trades.reduce((a, t) => a + t.R, 0) / trades.length : null
  const win = trades.length ? Math.round((100 * trades.filter((t) => t.R > 0).length) / trades.length) : 0
  return (
    <Section
      title="Backtest trades"
      description={`${trades.length} trades · avg ${signed(avg, 3)}R after costs · ${win}% profitable`}
      action={
        <div className="flex gap-2">
          <Select value={setup ?? null} onValueChange={(v) => navigate({ search: (s) => ({ ...s, setup: v ?? undefined }), replace: true })}>
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
          <form
            onSubmit={(e) => {
              e.preventDefault()
              navigate({ search: (s) => ({ ...s, symbol: typed.trim() || undefined }), replace: true })
            }}
          >
            <Input className="w-32" placeholder="Symbol ⏎" value={typed} onChange={(e) => setTyped(e.target.value.toUpperCase())} />
          </form>
        </div>
      }
    >
      {!trades.length ? (
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
              {[...trades].reverse().slice(0, 500).map((t, i) => (
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
          {trades.length > 500 && <p className="p-2 text-xs text-muted-foreground">Showing the newest 500 of {trades.length}.</p>}
        </div>
      )}
    </Section>
  )
}
