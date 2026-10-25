import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { q } from "@/lib/api"
import { Empty, ErrorState, isNotFound, Loading, PageHeader } from "@/components/common"
import { ScanView } from "@/components/scan-view"

export const Route = createFileRoute("/")({
  component: Today,
})

function Today() {
  const scan = useQuery(q.scan("latest"))
  return (
    <>
      <PageHeader
        title="Today"
        description={scan.data ? `Latest scan #${scan.data.id} · ${scan.data.created}` : "Latest scan of NIFTY 500 stocks"}
      />
      {scan.isPending ? (
        <Loading rows={6} />
      ) : isNotFound(scan.error) ? (
        <Empty>No scans yet. Press “Run scan” to download prices and find today’s setups (takes a minute or two).</Empty>
      ) : scan.error ? (
        <ErrorState error={scan.error} />
      ) : (
        <ScanView scan={scan.data} />
      )}
    </>
  )
}
