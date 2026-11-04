import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'

export const userKeys = {
  all: ['users'] as const,
  search: (q: string) => ['users', 'search', q] as const,
}

export function useUsers(q = '', { enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: userKeys.search(q),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/users', { params: { query: { q: q || undefined, limit: 100 } } })),
    placeholderData: keepPreviousData,
    enabled,
  })
}

export function useCreateUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { email: string; name: string; password: string }) =>
      unwrap(await api.POST('/api/v1/users', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userKeys.all }),
  })
}

export function useSetRole() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: 'member' | 'triager' }) =>
      unwrap(
        await api.PUT('/api/v1/users/{user_id}/role', {
          params: { path: { user_id: userId } },
          body: { role },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userKeys.all }),
  })
}
