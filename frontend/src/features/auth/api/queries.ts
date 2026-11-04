import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'
import { ApiError } from '@/lib/api/errors'
import type { Me } from '@/lib/api/types'

export const authKeys = {
  me: ['me'] as const,
}

/** The signed-in user, or null when nobody is signed in (a 401 is an answer, not a failure). */
export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: async (): Promise<Me | null> => {
      try {
        return unwrap(await api.GET('/api/v1/me'))
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
    staleTime: 5 * 60_000,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: { email: string; password: string }) =>
      unwrap(await api.POST('/api/v1/auth/login', { body })),
    onSuccess: (me) => {
      // Nothing cached for a previous user may be shown to this one.
      queryClient.clear()
      queryClient.setQueryData(authKeys.me, me)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await api.POST('/api/v1/auth/logout')
    },
    onSuccess: () => {
      queryClient.clear()
      queryClient.setQueryData(authKeys.me, null)
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (body: { current_password: string; new_password: string }) => {
      await api.POST('/api/v1/auth/password', { body })
    },
  })
}
