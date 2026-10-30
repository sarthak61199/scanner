import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { createRouter, RouterProvider } from "@tanstack/react-router"

import "./index.css"
import { routeTree } from "./routeTree.gen"
import { ThemeProvider } from "@/components/theme-provider.tsx"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { ErrorState, Loading } from "@/components/common"

// Data comes from route loaders; each route sets its own staleTime/gcTime. router.invalidate() reloads the page's data.
const router = createRouter({
  routeTree,
  defaultPreload: false,
  defaultPreloadStaleTime: 30_000,
  defaultPendingComponent: () => <Loading rows={6} />,
  defaultPendingMs: 300,
  defaultErrorComponent: ({ error }) => <ErrorState error={error} />,
})

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <TooltipProvider>
        <RouterProvider router={router} />
        <Toaster />
      </TooltipProvider>
    </ThemeProvider>
  </StrictMode>
)
