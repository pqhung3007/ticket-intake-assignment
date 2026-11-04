import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router'

import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { authKeys } from '@/features/auth'
import { ApiError } from '@/lib/api/errors'

import { router } from './router'
import { ThemeProvider } from './theme'

/** An expired or revoked session surfaces as a 401 anywhere; mark the user signed out so RequireAuth redirects. */
function onUnauthenticated(error: unknown) {
  if (error instanceof ApiError && error.status === 401 && queryClient.getQueryData(authKeys.me)) {
    queryClient.setQueryData(authKeys.me, null)
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: onUnauthenticated }),
  mutationCache: new MutationCache({ onError: onUnauthenticated }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true,
      // Retry transient failures only; 4xx answers won't change on retry.
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
})

export function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <RouterProvider router={router} />
          <Toaster position="bottom-right" richColors closeButton />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
