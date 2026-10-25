import { useMemo, useState } from "react"
import { createFileRoute, getRouteApi } from "@tanstack/react-router"

import { api, type ResearchRow, type Validated } from "@/lib/api"
import { num, pct, rClass, signed } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Empty, PageHeader, Section } from "@/components/common"

export const Route = createFileRoute("/research")({
  loader: () => api.research("latest"),
  staleTime: 5 * 60_000, // changes only when a research job finishes (which invalidates everything)
  component: Research,
})

const root = getRouteApi("__root__")

const key = (r: { setup: string; filters: string[] }) => [r.setup, ...r.filters].join("+")

function ValidatedCards({ v }: { v: Validated }) {
  const { config } = root.useLoaderData()
  if (!v.setups.length) return <Empty>No setup passed. The scanner sits out until one does.</Empty>
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {v.setups.map((s) => (
        <Card key={key(s)}>
          <CardHeader>
            <CardTitle>{key(s)}</CardTitle>
            <CardDescription>
              {s.exit} exit, {s.stop_atr}×ATR stop
              {config.exit_rules[s.exit] && <span className="block pt-1">{config.exit_rules[s.exit]}</span>}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3 text-sm">
              {(
                [
                  ["Train avg R", s.train.avg_r, `${s.train.n} trades`],
                  ["Test avg R", s.test.avg_r, `${s.test.n} trades, ${pct(s.test.win, 0)} win`],
                  [`${config.max_open}-slot test`, s.test.taken_avg_r, `DD ${num(s.test.max_dd_r, 1)}R`],
                ] as const
              ).map(([label, value, hint]) => (
                <div key={label}>
                  <div className="text-xs text-muted-foreground">{label}</div>
                  <div className={cn("text-lg font-semibold", rClass(value))}>{signed(value, 3)}</div>
                  <div className="text-xs text-muted-foreground">{hint}</div>
                </div>
              ))}
            </div>
            <div>
              <div className="mb-1.5 text-xs text-muted-foreground">By year (avg R)</div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(s.by_year).map(([y, b]) => (
                  <Badge key={y} variant="outline" className={rClass(b.avg_r)}>
                    {y}: {signed(b.avg_r)} <span className="text-muted-foreground">({b.n})</span>
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function AllRows({ rows }: { rows: ResearchRow[] }) {
  const [tab, setTab] = useState("passed")
  const [filter, setFilter] = useState("")
  const shown = useMemo(() => {
    const f = filter.toLowerCase()
    return rows
      .filter((r) => (tab === "passed" ? !r.fails.length : tab === "near" ? r.fails.length === 1 : true))
      .filter((r) => !f || `${key(r)} ${r.exit}`.toLowerCase().includes(f))
      .sort((a, b) => (b.test.avg_r ?? -99) - (a.test.avg_r ?? -99))
  }, [rows, tab, filter])
  const passed = rows.filter((r) => !r.fails.length).length
  return (
    <Section
      title="All combinations"
      description={`${rows.length} tested, ${passed} passed. Testing many combinations means some pass by luck.`}
      action={<Input className="w-48" placeholder="Filter setups…" value={filter} onChange={(e) => setFilter(e.target.value)} />}
    >
      <Tabs value={tab} onValueChange={setTab} className="mb-4">
        <TabsList>
          <TabsTrigger value="passed">Passed ({passed})</TabsTrigger>
          <TabsTrigger value="near">Failed one rule</TabsTrigger>
          <TabsTrigger value="all">All</TabsTrigger>
        </TabsList>
      </Tabs>
      {!shown.length ? (
        <Empty>Nothing matches.</Empty>
      ) : (
        <div className="max-h-[36rem] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-card">
              <TableRow>
                <TableHead>Setup</TableHead>
                <TableHead>Exit / stop</TableHead>
                <TableHead className="text-right">Train n</TableHead>
                <TableHead className="text-right">Train R</TableHead>
                <TableHead className="text-right">Test n</TableHead>
                <TableHead className="text-right">Test R</TableHead>
                <TableHead className="text-right">Slot R</TableHead>
                <TableHead className="text-right">DD</TableHead>
                <TableHead>Failed rules</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shown.map((r) => (
                <TableRow key={`${key(r)}-${r.exit}-${r.stop_atr}`}>
                  <TableCell className="font-medium">{key(r)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {r.exit} · {r.stop_atr}×
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{r.train.n}</TableCell>
                  <TableCell className={cn("text-right", rClass(r.train.avg_r))}>{signed(r.train.avg_r, 3)}</TableCell>
                  <TableCell className="text-right tabular-nums">{r.test.n}</TableCell>
                  <TableCell className={cn("text-right", rClass(r.test.avg_r))}>{signed(r.test.avg_r, 3)}</TableCell>
                  <TableCell className={cn("text-right", rClass(r.test.taken_avg_r))}>{signed(r.test.taken_avg_r, 3)}</TableCell>
                  <TableCell className="text-right tabular-nums">{num(r.test.max_dd_r, 1)}</TableCell>
                  <TableCell className="max-w-80 text-xs whitespace-normal text-muted-foreground">
                    {r.fails.length ? r.fails.join("; ") : <Badge variant="outline" className="text-positive">passed</Badge>}
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

function Research() {
  const run = Route.useLoaderData()
  const v = run?.validated
  return (
    <>
      <PageHeader
        title="Research"
        description={
          run
            ? `Run #${run.id} · ${run.created} · train before ${run.test_start}, test after (held out)`
            : "Every setup × filter × exit × stop width, tested on train and held-out test periods."
        }
      />
      {!run ? (
        <Empty>No research run yet. Press “Research” to run one (a few minutes).</Empty>
      ) : (
        <div className="space-y-6">
          {v && (
            <div>
              <h2 className="mb-1 text-lg font-semibold">Validated setups</h2>
              <p className="mb-4 text-sm text-muted-foreground">
                The best passing combination per setup; only these are scanned. Rules: train n ≥ {v.rules.min_train_n}, avg R &gt;{" "}
                {v.rules.min_train_avg_r}; test n ≥ {v.rules.min_test_n}, avg R ≥ {v.rules.min_test_avg_r}; test drawdown ≤{" "}
                {v.rules.max_test_dd_r}R; positive without its best year; a filter must beat the unfiltered setup.
              </p>
              <ValidatedCards v={v} />
            </div>
          )}
          {run.rows ? <AllRows rows={run.rows} /> : <Empty>This run has no per-combination results.</Empty>}
        </div>
      )}
    </>
  )
}
