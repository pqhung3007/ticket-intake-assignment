import { Pencil } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { ApiError } from '@/lib/api/errors'
import type { Ticket } from '@/lib/api/types'

import { useUpdateTicket } from '../api/mutations'
import { type TicketFormValues, toTicketPayload } from '../schemas'
import { handleMutationError } from './handleMutationError'
import { TicketForm } from './TicketForm'

function toFormValues(t: Ticket): TicketFormValues {
  return {
    title: t.title,
    target_app: t.target_app,
    severity: t.severity,
    description: t.description,
    steps_to_reproduce: t.steps_to_reproduce ?? '',
    expected_behavior: t.expected_behavior ?? '',
    actual_behavior: t.actual_behavior ?? '',
    environment: t.environment ?? '',
    confidential: t.confidential,
  }
}

export function EditTicketDialog({ ticket }: { ticket: Ticket }) {
  const [open, setOpen] = useState(false)
  const update = useUpdateTicket(ticket.number)

  const onSubmit = (values: TicketFormValues) =>
    update.mutate(
      { ...toTicketPayload(values), version: ticket.version },
      {
        onSuccess: () => {
          toast.success('Ticket updated')
          setOpen(false)
        },
        onError: (error) => {
          handleMutationError(error)
          if (error instanceof ApiError && error.code === 'version_conflict') setOpen(false)
        },
      },
    )

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) update.reset()
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Pencil aria-hidden />
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit #{ticket.number}</DialogTitle>
          <DialogDescription>Changes are recorded in the ticket&apos;s activity.</DialogDescription>
        </DialogHeader>
        {/* Keyed by version so the form resets if the ticket changes underneath. */}
        <TicketForm
          key={ticket.version}
          defaultValues={toFormValues(ticket)}
          onSubmit={onSubmit}
          submitLabel="Save changes"
          pending={update.isPending}
          serverErrors={update.error instanceof ApiError ? update.error.fieldErrors : undefined}
          onCancel={() => setOpen(false)}
        />
      </DialogContent>
    </Dialog>
  )
}
