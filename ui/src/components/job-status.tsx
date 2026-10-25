import { LoaderCircleIcon } from "lucide-react"

import type { Job, JobStatus } from "@/lib/api"
import { Badge } from "@/components/ui/badge"

export function JobStatusBadge({ status }: { status: JobStatus }) {
  if (status === "done") return <Badge variant="outline" className="text-positive">done</Badge>
  if (status === "failed") return <Badge variant="destructive">failed</Badge>
  return (
    <Badge variant="secondary">
      <LoaderCircleIcon className="animate-spin" /> {status}
    </Badge>
  )
}

export function duration(j: Job) {
  if (!j.started) return "–"
  const end = j.finished ? new Date(j.finished.replace(" ", "T")) : new Date()
  const s = Math.max(0, Math.round((end.getTime() - new Date(j.started.replace(" ", "T")).getTime()) / 1000))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}
