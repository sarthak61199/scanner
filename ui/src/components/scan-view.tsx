import { Fragment, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronDownIcon } from "lucide-react"

import { q, type Plan, type Scan } from "@/lib/api"
import { num, pct, rClass, rupees, signed, timeAgo } from "@/lib/format"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Empty, Section, Stat } from "@/components/common"
import { MoodCard } from "@/components/mood"

const CONVICTION: Record<string, string> = {
  HIGH: "border-positive/40 text-positive",
  MEDIUM: "",
  LOW: "border-negative/40 text-negative",
}

/** Claude notes use "**Heading:** text" lines; render the bold parts without a markdown library. */
function Note({ text }: { text: string }) {
  return (
    <div className="space-y-1.5 text-sm leading-relaxed">
      {text.split("\n").filter(Boolean).map((line, i) => (
        <p key={i}>
          {line.split(/(\*\*[^*]+\*\*)/).map((part, j) =>
            part.startsWith("**") ? <strong key={j}>{part.slice(2, -2)}</strong> : <Fragment key={j}>{part}</Fragment>
          )}
        </p>
      ))}
    </div>
  )
}

export function StockLink({ symbol, sector }: { symbol: string; sector?: string }) {
  return (
    <Link to="/stocks/$symbol" params={{ symbol }} search={{ sector }} className="font-medium hover:underline">
      {symbol}
    </Link>
  )
}

function PlansTable({ plans }: { plans: Plan[] }) {
  const [open, setOpen] = useState<number | null>(null)
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Stock</TableHead>
          <TableHead>Setup</TableHead>
          <TableHead className="text-right">Entry</TableHead>
          <TableHead className="text-right">Stop</TableHead>
          <TableHead className="text-right">Target</TableHead>
          <TableHead className="text-right">Qty</TableHead>
          <TableHead className="text-right">Test avg R</TableHead>
          <TableHead>Conviction</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {plans.map((p, i) => (
          <Fragment key={`${p.symbol}-${p.setup}`}>
            <TableRow>
              <TableCell>
                <StockLink symbol={p.symbol} sector={p.sector} />
                <div className="text-xs text-muted-foreground">{p.sector}</div>
              </TableCell>
              <TableCell>
                <div className="text-sm">{p.setup}</div>
                <div className="text-xs text-muted-foreground">{p.exit} exit · score {num(p.score)}</div>
              </TableCell>
              <TableCell className="text-right tabular-nums">{rupees(p.entry)}</TableCell>
              <TableCell className="text-right tabular-nums text-negative">{rupees(p.stop)}</TableCell>
              <TableCell className="text-right tabular-nums">{p.target === "trail" ? "trailing" : rupees(p.target)}</TableCell>
              <TableCell className="text-right tabular-nums">{p.qty}</TableCell>
              <TableCell className={cn("text-right", rClass(p.test_avgR))}>{signed(p.test_avgR, 3)}</TableCell>
              <TableCell>
                {p.conviction && p.conviction !== "-" ? (
                  <Badge variant="outline" className={CONVICTION[p.conviction]}>
                    {p.conviction}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">–</span>
                )}
              </TableCell>
              <TableCell className="text-right">
                {p.note && (
                  <Button variant="ghost" size="sm" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                    Analysis <ChevronDownIcon className={cn("transition-transform", open === i && "rotate-180")} />
                  </Button>
                )}
              </TableCell>
            </TableRow>
            {open === i && p.note && (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={9} className="bg-muted/40 whitespace-normal">
                  <Note text={p.note} />
                </TableCell>
              </TableRow>
            )}
          </Fragment>
        ))}
      </TableBody>
    </Table>
  )
}

export function ScanView({ scan }: { scan: Scan }) {
  const validated = useQuery(q.validated())
  const config = useQuery(q.config())
  const top = scan.sectors[0]
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Trade plans" value={scan.plans.length} hint={`${scan.rejected.length} rejected on fundamentals`} />
        <Stat
          label="Validated setups"
          value={validated.data?.setups.length ?? "–"}
          hint={validated.data ? `researched ${validated.data.age_days}d ago` : undefined}
        />
        <Stat label="Strongest sector" value={<span className="text-base">{top?.sector ?? "–"}</span>} hint={top && `3m ${pct(top.ret63)}`} />
        <Stat
          label="Scanned"
          value={<span className="text-base">{timeAgo(scan.created)}</span>}
          hint={
            config.data && `${config.data.risk_pct}% risk/trade · max ${config.data.max_open} open · ₹${config.data.capital.toLocaleString("en-IN")}`
          }
        />
      </div>

      <MoodCard mood={scan.mood} />

      {scan.plans.length ? (
        <Section title="Trade plans" description="Stocks where a validated setup triggered at the last close, ranked by score.">
          <PlansTable plans={scan.plans} />
        </Section>
      ) : (
        <Section
          title="Watchlist"
          description="No validated setup triggered today. Strongest-ranked stocks to watch instead."
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Stock</TableHead>
                <TableHead>Sector</TableHead>
                <TableHead className="text-right">Score</TableHead>
                <TableHead className="text-right">Close</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scan.watchlist.map((w) => (
                <TableRow key={w.sym}>
                  <TableCell>
                    <StockLink symbol={w.sym} sector={w.sector} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">{w.sector}</TableCell>
                  <TableCell className="text-right tabular-nums">{num(w.score)}</TableCell>
                  <TableCell className="text-right tabular-nums">{rupees(w.close)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Section>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <Section title="Sector strength" description="Median 3m/6m return of members and % above the 200-day average.">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Sector</TableHead>
                <TableHead className="text-right">3m</TableHead>
                <TableHead className="text-right">6m</TableHead>
                <TableHead className="text-right">&gt; 200DMA</TableHead>
                <TableHead className="text-right">Score</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scan.sectors.map((s) => (
                <TableRow key={s.sector}>
                  <TableCell className="max-w-56 truncate">
                    {s.sector} <span className="text-xs text-muted-foreground">({s.n})</span>
                  </TableCell>
                  <TableCell className={cn("text-right", rClass(s.ret63))}>{pct(s.ret63)}</TableCell>
                  <TableCell className={cn("text-right", rClass(s.ret126))}>{pct(s.ret126)}</TableCell>
                  <TableCell className="text-right tabular-nums">{pct(s.breadth, 0)}</TableCell>
                  <TableCell className="text-right tabular-nums">{num(s.score)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Section>
        <Section title="Rejected on fundamentals" description="Setups that triggered but failed the NSE filings red-flag check.">
          {scan.rejected.length ? (
            <ul className="divide-y text-sm">
              {scan.rejected.map((r) => (
                <li key={`${r.symbol}-${r.setup}`} className="py-2.5">
                  <StockLink symbol={r.symbol} /> <span className="text-xs text-muted-foreground">{r.setup}</span>
                  <div className="text-xs text-negative">{r.red_flags}</div>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>None this scan.</Empty>
          )}
        </Section>
      </div>
    </div>
  )
}
