import { useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"

import { q } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { ErrorState, Loading, PageHeader, Section } from "@/components/common"
import { duration, JobStatusBadge } from "@/components/job-status"

export const Route = createFileRoute("/jobs/$jobId")({
  component: JobPage,
})

function JobPage() {
  const id = Number(Route.useParams().jobId)
  const job = useQuery(q.job(id))
  const logRef = useRef<HTMLPreElement>(null)
  const log = job.data?.log ?? ""

  // keep the newest output in view while the job runs
  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [log])

  return (
    <>
      <PageHeader
        title={`Job #${id}`}
        description={job.data && `${job.data.kind} · created ${job.data.created} · ${duration(job.data)}`}
        actions={
          job.data?.status === "done" &&
          (job.data.kind === "scan" ? (
            <Button render={<Link to="/" />}>View scan</Button>
          ) : (
            <Button render={<Link to="/research" />}>View research</Button>
          ))
        }
      />
      {job.isPending ? (
        <Loading />
      ) : job.error ? (
        <ErrorState error={job.error} />
      ) : (
        <Section title="Output" action={<JobStatusBadge status={job.data.status} />}>
          {job.data.error && <ErrorState error={job.data.error} />}
          <pre ref={logRef} className="mt-3 max-h-[60vh] overflow-auto rounded-lg bg-muted p-4 font-mono text-xs leading-relaxed">
            {log || "Waiting for output…"}
          </pre>
        </Section>
      )}
    </>
  )
}
