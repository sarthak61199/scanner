import { createRootRoute, Link, Outlet } from "@tanstack/react-router"
import { ActivityIcon, ClockIcon, MoonIcon, SunIcon } from "lucide-react"

import { api } from "@/lib/api"
import { JobControls } from "@/components/job-controls"
import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"

// App-wide data used by the header and several pages; components deep in the tree read it with getRouteApi("__root__").
export const Route = createRootRoute({
  loader: async () => {
    const [config, schedule, jobs, validated] = await Promise.all([api.config(), api.schedule(), api.jobs(), api.validated()])
    return { config, schedule, jobs, validated }
  },
  staleTime: 30_000,
  component: RootLayout,
  notFoundComponent: () => <p className="text-muted-foreground">Page not found.</p>,
})

const NAV = [
  { to: "/", label: "Today" },
  { to: "/journal", label: "Journal" },
  { to: "/scans", label: "Scans" },
  { to: "/research", label: "Research" },
  { to: "/news", label: "News" },
  { to: "/jobs", label: "Jobs" },
] as const

function RootLayout() {
  const { schedule } = Route.useLoaderData()
  const { theme, setTheme } = useTheme()
  const dark = theme === "dark" || (theme === "system" && matchMedia("(prefers-color-scheme: dark)").matches)
  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-20 border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <ActivityIcon className="size-5" />
            Scanner
          </Link>
          <nav className="flex flex-1 items-center gap-1 overflow-x-auto text-sm">
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                activeOptions={{ exact: n.to === "/" }}
                className="rounded-md px-2.5 py-1.5 text-muted-foreground hover:text-foreground data-[status=active]:bg-muted data-[status=active]:text-foreground"
              >
                {n.label}
              </Link>
            ))}
          </nav>
          {schedule.enabled && (
            <Link to="/jobs" className="hidden items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground md:flex">
              <ClockIcon className="size-3.5" /> next scan {schedule.next_scan.slice(5, 16)}
            </Link>
          )}
          <JobControls />
          <Button variant="ghost" size="icon" aria-label="Toggle theme" onClick={() => setTheme(dark ? "light" : "dark")}>
            {dark ? <SunIcon /> : <MoonIcon />}
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-muted-foreground">
        Research tool. Not investment advice.
      </footer>
    </div>
  )
}
