import { useQuery } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'

export const authKeys = {
  me: ['me'] as const,
}

export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: async () => unwrap(await api.GET('/api/v1/me')),
    staleTime: 5 * 60_000,
  })
}
