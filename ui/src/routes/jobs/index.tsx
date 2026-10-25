import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"

import { q } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Empty, ErrorState, Loading, PageHeader, Section } from "@/components/common"
import { duration, JobStatusBadge } from "@/components/job-status"

export const Route = createFileRoute("/jobs/")({
  component: Jobs,
})

function Jobs() {
  const jobs = useQuery(q.jobs())
  const schedule = useQuery(q.schedule())
  return (
    <>
      <PageHeader
        title="Jobs"
        description={
          schedule.data?.enabled
            ? `Scans run automatically on weekdays at ${schedule.data.scan_time} IST (next ${schedule.data.next_scan}); research weekly (next ${schedule.data.next_research}). One job runs at a time, and only while the server is up.`
            : "Scheduler is off (SCHEDULER=false). Scans and research run only when started here. One job runs at a time."
        }
      />
      <Section title="Recent jobs">
        {jobs.isPending ? (
          <Loading />
        ) : jobs.error ? (
          <ErrorState error={jobs.error} />
        ) : !jobs.data.length ? (
          <Empty>No jobs yet.</Empty>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job</TableHead>
                <TableHead>Kind</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead className="text-right">Took</TableHead>
                <TableHead>Error</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.data.map((j) => (
                <TableRow key={j.id}>
                  <TableCell>
                    <Link to="/jobs/$jobId" params={{ jobId: String(j.id) }} className="font-medium hover:underline">
                      #{j.id}
                    </Link>
                  </TableCell>
                  <TableCell>
                    {j.kind}
                    {j.trigger === "schedule" && (
                      <Badge variant="outline" className="ml-2">
                        scheduled
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <JobStatusBadge status={j.status} />
                  </TableCell>
                  <TableCell className="tabular-nums">{j.started ?? j.created}</TableCell>
                  <TableCell className="text-right tabular-nums">{duration(j)}</TableCell>
                  <TableCell className="max-w-80 truncate text-xs text-negative">{j.error}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>
    </>
  )
}
