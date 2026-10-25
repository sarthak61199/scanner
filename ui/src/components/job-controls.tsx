import { useEffect, useRef, useState } from "react"
import { getRouteApi, Link, useRouter } from "@tanstack/react-router"
import { FlaskConicalIcon, LoaderCircleIcon, PlayIcon } from "lucide-react"
import { toast } from "sonner"

import { api, ApiError, isActive, type JobKind } from "@/lib/api"
import { usePoll } from "@/hooks/use-poll"
import { Button } from "@/components/ui/button"

const root = getRouteApi("__root__")

/** Run scan / research buttons; while a job runs, polls the root loader and reloads all data when it finishes. */
export function JobControls() {
  const router = useRouter()
  const { jobs } = root.useLoaderData()
  const active = jobs.find(isActive)
  const [starting, setStarting] = useState(false)
  const wasActive = useRef<number | null>(null)

  usePoll(!!active, "__root__", 3000)

  useEffect(() => {
    if (active) {
      wasActive.current = active.id
      return
    }
    const id = wasActive.current
    if (id == null) return
    wasActive.current = null
    const job = jobs.find((j) => j.id === id)
    if (job?.status === "done") toast.success(`${job.kind === "scan" ? "Scan" : "Research"} #${id} finished`)
    if (job?.status === "failed") toast.error(`Job #${id} failed`, { description: job.error ?? undefined })
    router.invalidate()
  }, [active, jobs, router])

  async function start(kind: JobKind) {
    setStarting(true)
    try {
      const job = await api.startJob(kind)
      toast(`${kind === "scan" ? "Scan" : "Research"} started`, { description: `Job #${job.id}` })
    } catch (e) {
      toast.error(e instanceof ApiError && e.status === 409 ? "A job is already running" : String(e))
    } finally {
      setStarting(false)
      router.invalidate({ filter: (m) => m.routeId === "__root__" })
    }
  }

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
      <Button size="sm" disabled={starting} onClick={() => start("scan")}>
        <PlayIcon /> Run scan
      </Button>
      <Button size="sm" variant="outline" disabled={starting} onClick={() => start("research")}>
        <FlaskConicalIcon /> Research
      </Button>
    </div>
  )
}
