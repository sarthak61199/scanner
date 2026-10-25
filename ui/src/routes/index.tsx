import { createFileRoute } from "@tanstack/react-router"

import { api } from "@/lib/api"
import { Empty, PageHeader } from "@/components/common"
import { ScanView } from "@/components/scan-view"

export const Route = createFileRoute("/")({
  loader: () => api.scan("latest"),
  staleTime: 60_000,
  component: Today,
})

function Today() {
  const scan = Route.useLoaderData()
  return (
    <>
      <PageHeader
        title="Today"
        description={scan ? `Latest scan #${scan.id} · ${scan.created}` : "Latest scan of NIFTY 500 stocks"}
      />
      {scan ? (
        <ScanView scan={scan} />
      ) : (
        <Empty>No scans yet. Press “Run scan” to download prices and find today’s setups (takes a minute or two).</Empty>
      )}
    </>
  )
}
