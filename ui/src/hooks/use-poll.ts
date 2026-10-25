import { useEffect } from "react"
import { useRouter } from "@tanstack/react-router"

/** While `active`, re-run the loader of route `routeId` every `ms` (e.g. a running job's status and log). */
export function usePoll(active: boolean, routeId: string, ms = 2000) {
  const router = useRouter()
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => router.invalidate({ filter: (m) => m.routeId === routeId }), ms)
    return () => clearInterval(t)
  }, [active, routeId, ms, router])
}
