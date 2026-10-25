import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"

import { q } from "@/lib/api"
import { moodLabel, signed } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Empty, ErrorState, Loading, PageHeader, Section } from "@/components/common"

export const Route = createFileRoute("/scans/")({
  component: Scans,
})

function Scans() {
  const scans = useQuery(q.scans())
  return (
    <>
      <PageHeader title="Scans" description="Every saved scan, newest first." />
      <Section title="History">
        {scans.isPending ? (
          <Loading />
        ) : scans.error ? (
          <ErrorState error={scans.error} />
        ) : !scans.data.length ? (
          <Empty>No scans yet.</Empty>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Scan</TableHead>
                <TableHead>Time</TableHead>
                <TableHead>Plans</TableHead>
                <TableHead>Mood</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scans.data.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <Link to="/scans/$scanId" params={{ scanId: String(s.id) }} className="font-medium hover:underline">
                      #{s.id}
                    </Link>
                  </TableCell>
                  <TableCell className="tabular-nums">{s.created}</TableCell>
                  <TableCell>
                    {s.n_plans ? (
                      <div className="flex flex-wrap gap-1">
                        {s.symbols.map((sym, i) => (
                          <Badge key={`${sym}-${i}`} variant="secondary">
                            {sym}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <span className="text-muted-foreground">none (watchlist)</span>
                    )}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {s.mood_score == null ? "–" : `${signed(s.mood_score)} ${moodLabel(s.mood_score)}`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>
    </>
  )
}
