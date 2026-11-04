import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronRight, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Field } from '@/components/common/Field'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

import { SEVERITIES, SEVERITY_META } from '../constants'
import { type TicketFormValues, ticketFormSchema } from '../schemas'

export function TicketForm({
  defaultValues,
  onSubmit,
  submitLabel,
  pending,
  serverErrors,
  onCancel,
}: {
  defaultValues: TicketFormValues
  onSubmit: (values: TicketFormValues) => void
  submitLabel: string
  pending: boolean
  /** Field errors returned by the API (e.g. a 400 validation_error), shown inline. */
  serverErrors?: Record<string, string>
  onCancel?: () => void
}) {
  const form = useForm<TicketFormValues>({ resolver: zodResolver(ticketFormSchema), defaultValues })
  const { register, control, handleSubmit, setError, formState } = form
  const errors = formState.errors

  const hasRepro = Boolean(
    defaultValues.steps_to_reproduce ||
    defaultValues.expected_behavior ||
    defaultValues.actual_behavior ||
    defaultValues.environment,
  )
  const [showRepro, setShowRepro] = useState(hasRepro)

  useEffect(() => {
    for (const [field, message] of Object.entries(serverErrors ?? {})) {
      if (field in defaultValues) setError(field as keyof TicketFormValues, { type: 'server', message })
    }
  }, [serverErrors, setError, defaultValues])

  const a11y = (name: keyof TicketFormValues) => ({
    id: name,
    'aria-invalid': errors[name] ? true : undefined,
    'aria-describedby': errors[name] ? `${name}-error` : `${name}-hint`,
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-6" noValidate>
      <Field id="title" label="Title" error={errors.title?.message} hint="What is broken, in one line.">
        <Input
          {...a11y('title')}
          {...register('title')}
          placeholder="CSV export times out for large reports"
        />
      </Field>

      <div className="grid gap-6 sm:grid-cols-2">
        <Field id="target_app" label="App" error={errors.target_app?.message} hint="The app the bug is in.">
          <Input {...a11y('target_app')} {...register('target_app')} placeholder="reports" />
        </Field>
        <Field id="severity" label="Severity" error={errors.severity?.message}>
          <Controller
            control={control}
            name="severity"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="severity" className="w-full [&_[data-desc]]:hidden">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITIES.map((s) => (
                    <SelectItem key={s} value={s}>
                      <span className="font-medium">{SEVERITY_META[s].label}</span>
                      <span data-desc className="text-muted-foreground">
                        — {SEVERITY_META[s].description}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        </Field>
      </div>

      <Field
        id="description"
        label="Description"
        optional
        error={errors.description?.message}
        hint="Context: what you were doing, how often it happens, who is affected."
      >
        <Textarea {...a11y('description')} {...register('description')} rows={5} />
      </Field>

      <div className="rounded-lg border">
        <button
          type="button"
          onClick={() => setShowRepro((v) => !v)}
          aria-expanded={showRepro}
          className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm font-medium"
        >
          <ChevronRight className={cn('size-4 transition-transform', showRepro && 'rotate-90')} aria-hidden />
          Reproduction details
          <span className="text-muted-foreground font-normal">— speeds up the fix</span>
        </button>
        {showRepro && (
          <div className="grid gap-6 border-t p-4">
            <Field
              id="steps_to_reproduce"
              label="Steps to reproduce"
              optional
              error={errors.steps_to_reproduce?.message}
            >
              <Textarea
                {...a11y('steps_to_reproduce')}
                {...register('steps_to_reproduce')}
                rows={4}
                placeholder={'1. Open Reports\n2. Choose "Last 12 months"\n3. Click Export → CSV'}
              />
            </Field>
            <div className="grid gap-6 sm:grid-cols-2">
              <Field
                id="expected_behavior"
                label="Expected"
                optional
                error={errors.expected_behavior?.message}
              >
                <Textarea {...a11y('expected_behavior')} {...register('expected_behavior')} rows={3} />
              </Field>
              <Field id="actual_behavior" label="Actual" optional error={errors.actual_behavior?.message}>
                <Textarea {...a11y('actual_behavior')} {...register('actual_behavior')} rows={3} />
              </Field>
            </div>
            <Field
              id="environment"
              label="Environment"
              optional
              error={errors.environment?.message}
              hint="Browser, OS, app version or account."
            >
              <Input {...a11y('environment')} {...register('environment')} placeholder="Chrome 141, macOS" />
            </Field>
          </div>
        )}
      </div>

      <Controller
        control={control}
        name="confidential"
        render={({ field }) => (
          <div className="flex items-start justify-between gap-4 rounded-lg border p-4">
            <div className="space-y-1">
              <label htmlFor="confidential" className="text-sm font-medium">
                Confidential
              </label>
              <p id="confidential-hint" className="text-muted-foreground text-xs">
                For security issues or sensitive data. Only you and triagers will see this ticket.
              </p>
            </div>
            <Switch
              id="confidential"
              checked={field.value}
              onCheckedChange={field.onChange}
              aria-describedby="confidential-hint"
            />
          </div>
        )}
      />

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={pending}>
          {pending && <Loader2 className="animate-spin" aria-hidden />}
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
