import { useEffect, useRef } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { FlaskConicalIcon, LoaderCircleIcon, PlayIcon } from "lucide-react"
import { toast } from "sonner"

import { api, ApiError, q, type JobKind } from "@/lib/api"
import { Button } from "@/components/ui/button"

/** Run scan / research buttons; while a job runs, shows it and refreshes data when it finishes. */
export function JobControls() {
  const qc = useQueryClient()
  const jobs = useQuery(q.jobs())
  const active = jobs.data?.find((j) => j.status === "queued" || j.status === "running")
  const wasActive = useRef<number | null>(null)

  useEffect(() => {
    if (active) {
      wasActive.current = active.id
      return
    }
    const id = wasActive.current
    if (id == null) return
    wasActive.current = null
    const job = jobs.data?.find((j) => j.id === id)
    if (job?.status === "done") toast.success(`${job.kind === "scan" ? "Scan" : "Research"} #${id} finished`)
    if (job?.status === "failed") toast.error(`Job #${id} failed`, { description: job.error ?? undefined })
    qc.invalidateQueries({ predicate: (query) => query.queryKey[0] !== "jobs" })
  }, [active, jobs.data, qc])

  const start = useMutation({
    mutationFn: (kind: JobKind) => api.startJob(kind),
    onSuccess: (job) => {
      toast(`${job.kind === "scan" ? "Scan" : "Research"} started`, { description: `Job #${job.id}` })
      qc.invalidateQueries({ queryKey: ["jobs"] })
    },
    onError: (e) => toast.error(e instanceof ApiError && e.status === 409 ? "A job is already running" : e.message),
  })

  if (active) {
    return (
      <Link to="/jobs/$jobId" params={{ jobId: String(active.id) }}>
        <Button variant="outline" size="sm">
          <LoaderCircleIcon className="animate-spin" />
          {active.kind === "scan" ? "Scanning" : "Researching"}… #{active.id}
        </Button>
      </Link>
    )
  }
  return (
    <div className="flex gap-2">
      <Button size="sm" disabled={start.isPending} onClick={() => start.mutate("scan")}>
        <PlayIcon /> Run scan
      </Button>
      <Button size="sm" variant="outline" disabled={start.isPending} onClick={() => start.mutate("research")}>
        <FlaskConicalIcon /> Research
      </Button>
    </div>
  )
}
