import { z } from 'zod'

import type { TicketCreateInput } from '@/lib/api/types'

/** Mirrors the backend limits so users get instant feedback; the server remains the authority. */
export const ticketFormSchema = z.object({
  title: z.string().trim().min(3, 'At least 3 characters').max(120, 'At most 120 characters'),
  target_app: z.string().trim().min(1, 'Which app is the bug in?').max(80, 'At most 80 characters'),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  description: z.string().trim().max(10_000, 'At most 10,000 characters'),
  steps_to_reproduce: z.string().trim().max(5_000, 'At most 5,000 characters'),
  expected_behavior: z.string().trim().max(2_000, 'At most 2,000 characters'),
  actual_behavior: z.string().trim().max(2_000, 'At most 2,000 characters'),
  environment: z.string().trim().max(500, 'At most 500 characters'),
  confidential: z.boolean(),
})

export type TicketFormValues = z.infer<typeof ticketFormSchema>

export const emptyTicketForm: TicketFormValues = {
  title: '',
  target_app: '',
  severity: 'medium',
  description: '',
  steps_to_reproduce: '',
  expected_behavior: '',
  actual_behavior: '',
  environment: '',
  confidential: false,
}

/** Empty optional text becomes null, matching the API's "not provided". */
export function toTicketPayload(values: TicketFormValues): Omit<TicketCreateInput, 'request_key'> {
  const orNull = (s: string) => (s.trim() ? s.trim() : null)
  return {
    ...values,
    steps_to_reproduce: orNull(values.steps_to_reproduce),
    expected_behavior: orNull(values.expected_behavior),
    actual_behavior: orNull(values.actual_behavior),
    environment: orNull(values.environment),
  }
}
