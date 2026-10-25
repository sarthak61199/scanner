import { useState } from "react"
import { createFileRoute, getRouteApi } from "@tanstack/react-router"

import { api, type JournalGroup, type JournalStats, type PaperTrade } from "@/lib/api"
import { pct, rClass, rupees, signed } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Empty, PageHeader, Section } from "@/components/common"
import { StockLink } from "@/components/scan-view"

export const Route = createFileRoute("/journal")({
  loader: async () => {
    const [stats, trades] = await Promise.all([api.journalStats(), api.journal()])
    return { stats, trades }
  },
  staleTime: 60_000,
  component: Journal,
})

const root = getRouteApi("__root__")

const ENOUGH = 30 // closed trades before live results say much

function SetupCards({ stats }: { stats: JournalStats }) {
  const setups = stats.by_setup.filter((s) => s.validated || s.all.n)
  if (!setups.length) return null
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {setups.map((s) => {
        const live = s.all.avg_r
        const early = s.all.closed < ENOUGH
        return (
          <Card key={s.variant}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {s.variant}
                {!s.validated && <Badge variant="outline">no longer validated</Badge>}
              </CardTitle>
              <CardDescription>
                {s.all.closed} closed, {s.all.open} open
                {early && ` · too early to judge (${ENOUGH - s.all.closed} more closed trades for ${ENOUGH})`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Paper avg R</div>
                  <div className={cn("text-2xl font-semibold", rClass(live), early && "opacity-60")}>{signed(live, 3)}</div>
                  <div className="text-xs text-muted-foreground">
                    {pct(s.all.win, 0)} win · total {signed(s.all.total_r, 1)}R
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Backtest test avg R</div>
                  <div className={cn("text-2xl font-semibold", rClass(s.backtest_test_avg_r))}>{signed(s.backtest_test_avg_r, 3)}</div>
                  <div className="text-xs text-muted-foreground">what research expected</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">5-slot account</div>
                  <div className={cn("text-2xl font-semibold", rClass(s.taken.avg_r), s.taken.closed < ENOUGH && "opacity-60")}>
                    {signed(s.taken.avg_r, 3)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    backtest {signed(s.backtest_slot_avg_r, 3)} · {s.taken.closed} closed
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function GroupTable({ rows }: { rows: [string, JournalGroup][] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead />
          <TableHead className="text-right">Closed</TableHead>
          <TableHead className="text-right">Open</TableHead>
          <TableHead className="text-right">Avg R</TableHead>
          <TableHead className="text-right">Win</TableHead>
          <TableHead className="text-right">Total R</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map(([label, g]) => (
          <TableRow key={label}>
            <TableCell>{label}</TableCell>
            <TableCell className="text-right tabular-nums">{g.closed}</TableCell>
            <TableCell className="text-right tabular-nums">{g.open}</TableCell>
            <TableCell className={cn("text-right", rClass(g.avg_r))}>{signed(g.avg_r, 3)}</TableCell>
            <TableCell className="text-right tabular-nums">{pct(g.win, 0)}</TableCell>
            <TableCell className={cn("text-right", rClass(g.total_r))}>{signed(g.total_r, 1)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function TradeFlags({ t }: { t: PaperTrade }) {
  return (
    <div className="flex flex-wrap gap-1">
      {t.taken && <Badge variant="secondary">taken</Badge>}
      {t.rejected && (
        <Tooltip>
          <TooltipTrigger render={<Badge variant="destructive">rejected</Badge>} />
          <TooltipContent>{t.rejected}</TooltipContent>
        </Tooltip>
      )}
      {t.conviction && <Badge variant="outline">{t.conviction}</Badge>}
    </div>
  )
}

function Trades({ trades }: { trades: PaperTrade[] }) {
  const [tab, setTab] = useState<"open" | "closed">("open")
  const shown = trades.filter((t) => t.status === tab)
  const open = tab === "open"
  return (
    <Section
      title="Paper trades"
      description="Entry at the signal day's close; managed with the setup's backtest exit rule. R is after costs."
      action={
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="open">Open ({trades.filter((t) => t.status === "open").length})</TabsTrigger>
            <TabsTrigger value="closed">Closed ({trades.filter((t) => t.status === "closed").length})</TabsTrigger>
          </TabsList>
        </Tabs>
      }
    >
      {!shown.length ? (
        <Empty>{open ? "No open paper trades." : "No closed paper trades yet."}</Empty>
      ) : (
        <div className="max-h-[36rem] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-card">
              <TableRow>
                <TableHead>Stock</TableHead>
                <TableHead>Setup</TableHead>
                <TableHead>Signal</TableHead>
                <TableHead className="text-right">Entry</TableHead>
                <TableHead className="text-right">{open ? "Stop now" : "Exit"}</TableHead>
                <TableHead className="text-right">{open ? "Last close" : "Reason"}</TableHead>
                <TableHead className="text-right">Days</TableHead>
                <TableHead className="text-right">{open ? "R now" : "R"}</TableHead>
                <TableHead>Flags</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shown.map((t) => (
                <TableRow key={t.id} className={cn(t.rejected && "opacity-70")}>
                  <TableCell>
                    <StockLink symbol={t.symbol} sector={t.sector} />
                    <div className="text-xs text-muted-foreground">{t.sector}</div>
                  </TableCell>
                  <TableCell className="text-xs">
                    {t.variant}
                    <div className="text-muted-foreground">
                      {t.exit_rule} · {t.stop_atr}×ATR
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">{t.signal_date}</TableCell>
                  <TableCell className="text-right tabular-nums">{rupees(t.entry)}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {open ? rupees(t.current_stop) : rupees(t.exit)}
                    {!open && <div className="text-xs text-muted-foreground">{t.exit_date}</div>}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{open ? rupees(t.last_close) : t.reason}</TableCell>
                  <TableCell className="text-right tabular-nums">{t.days}</TableCell>
                  <TableCell className={cn("text-right font-medium", rClass(t.R))}>{signed(t.R)}</TableCell>
                  <TableCell>
                    <TradeFlags t={t} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  )
}

function Journal() {
  const { stats: s, trades } = Route.useLoaderData()
  const { config } = root.useLoaderData()
  return (
    <>
      <PageHeader
        title="Journal"
        description={`Every trade plan, paper-traded with the backtest's exit rules: the honest forward test. "Taken" = the ${config.max_open}-slot account.`}
      />
      {!trades.length ? (
        <div className="space-y-6">
          <Empty>
            No paper trades yet. Each scan records its trade plans here and updates open ones, so results build up as the daily
            scan runs.
          </Empty>
          <SetupCards stats={s} />
        </div>
      ) : (
        <div className="space-y-6">
          <SetupCards stats={s} />
          <div className="grid gap-6 lg:grid-cols-2">
            <Section title="By Claude conviction" description="Do HIGH-conviction picks actually do better? (accepted trades)">
              <GroupTable rows={(["HIGH", "MEDIUM", "LOW", "none"] as const).map((k) => [k === "none" ? "no note" : k, s.by_conviction[k]])} />
            </Section>
            <Section title="Fundamentals filter" description="Rejected plans are paper-traded too, to test whether the red flags help.">
              <GroupTable
                rows={[
                  ["Accepted", s.overall.accepted],
                  ["Rejected on red flags", s.overall.rejected],
                  ["Taken (5-slot)", s.overall.taken],
                ]}
              />
            </Section>
          </div>
          <Trades trades={trades} />
        </div>
      )}
    </>
  )
}
