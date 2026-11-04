import { useMutation, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'
import { ApiError } from '@/lib/api/errors'
import type { TicketCreateInput, TicketUpdateInput } from '@/lib/api/types'

import { ticketKeys } from './keys'

export function useCreateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: TicketCreateInput) => unwrap(await api.POST('/api/v1/tickets', { body })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
      void queryClient.invalidateQueries({ queryKey: ticketKeys.stats() })
    },
  })
}

export function useUpdateTicket(number: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: TicketUpdateInput) =>
      unwrap(await api.PATCH('/api/v1/tickets/{number}', { params: { path: { number } }, body })),
    onSettled: (_data, error) => {
      // Refetch the detail on success (new version, new events) and on a version conflict
      // (so the user sees what changed before retrying).
      if (!error || (error instanceof ApiError && error.isConflict)) {
        void queryClient.invalidateQueries({ queryKey: ticketKeys.detail(number) })
      }
      if (!error) {
        void queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
        void queryClient.invalidateQueries({ queryKey: ticketKeys.stats() })
      }
    },
  })
}

export function useAddComment(number: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: string) =>
      unwrap(
        await api.POST('/api/v1/tickets/{number}/comments', { params: { path: { number } }, body: { body } }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ticketKeys.detail(number) }),
  })
}
