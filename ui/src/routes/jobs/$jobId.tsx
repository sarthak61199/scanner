import { useEffect, useRef } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"

import { api, isActive } from "@/lib/api"
import { usePoll } from "@/hooks/use-poll"
import { Button } from "@/components/ui/button"
import { ErrorState, PageHeader, Section } from "@/components/common"
import { duration, JobStatusBadge } from "@/components/job-status"

export const Route = createFileRoute("/jobs/$jobId")({
  loader: ({ params }) => api.job(Number(params.jobId)),
  staleTime: 0, // polled while the job runs
  component: JobPage,
})

function JobPage() {
  const job = Route.useLoaderData()
  const logRef = useRef<HTMLPreElement>(null)

  usePoll(isActive(job), Route.id)

  // keep the newest output in view while the job runs
  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [job.log])

  return (
    <>
      <PageHeader
        title={`Job #${job.id}`}
        description={`${job.kind} · created ${job.created} · ${duration(job)}`}
        actions={
          job.status === "done" &&
          (job.kind === "scan" ? (
            <Button render={<Link to="/" />}>View scan</Button>
          ) : (
            <Button render={<Link to="/research" />}>View research</Button>
          ))
        }
      />
      <Section title="Output" action={<JobStatusBadge status={job.status} />}>
        {job.error && <ErrorState error={job.error} />}
        <pre ref={logRef} className="mt-3 max-h-[60vh] overflow-auto rounded-lg bg-muted p-4 font-mono text-xs leading-relaxed">
          {job.log || "Waiting for output…"}
        </pre>
      </Section>
    </>
  )
}
