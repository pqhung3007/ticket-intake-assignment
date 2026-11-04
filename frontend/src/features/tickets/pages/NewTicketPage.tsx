import { useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { ApiError, errorMessage } from '@/lib/api/errors'

import { useCreateTicket } from '../api/mutations'
import { TicketForm } from '../components/TicketForm'
import { emptyTicketForm, type TicketFormValues, toTicketPayload } from '../schemas'

export function NewTicketPage() {
  const navigate = useNavigate()
  const create = useCreateTicket()
  // One idempotency key per form: a double-click or a retry after a network error
  // returns the same ticket instead of filing a duplicate.
  const [requestKey] = useState(() => `web-${crypto.randomUUID()}`)

  const onSubmit = (values: TicketFormValues) =>
    create.mutate(
      { ...toTicketPayload(values), request_key: requestKey },
      {
        onSuccess: ({ ticket }) => {
          toast.success(`Ticket #${ticket.number} filed`)
          void navigate(`/tickets/${ticket.number}`, { replace: true })
        },
        onError: (error) => {
          if (!(error instanceof ApiError && error.code === 'validation_error'))
            toast.error(errorMessage(error))
        },
      },
    )

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        title="Report a bug"
        description="A clear title and the app name are enough to start; details help it get fixed faster."
      />
      <Card>
        <CardContent>
          <TicketForm
            defaultValues={emptyTicketForm}
            onSubmit={onSubmit}
            submitLabel="File ticket"
            pending={create.isPending}
            serverErrors={create.error instanceof ApiError ? create.error.fieldErrors : undefined}
            onCancel={() => void navigate(-1)}
          />
        </CardContent>
      </Card>
    </div>
  )
}
