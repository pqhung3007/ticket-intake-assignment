import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Field } from '@/components/common/Field'
import { PageHeader } from '@/components/common/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { errorMessage } from '@/lib/api/errors'

import { useChangePassword, useCurrentUser } from '../api/queries'

const schema = z
  .object({
    current_password: z.string().min(1, 'Enter your current password'),
    new_password: z.string().min(10, 'Use at least 10 characters'),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: 'Passwords do not match' })
type Values = z.infer<typeof schema>

export function AccountPage() {
  const { data: me } = useCurrentUser()
  const change = useChangePassword()
  const { register, handleSubmit, reset, formState } = useForm<Values>({ resolver: zodResolver(schema) })
  const { errors } = formState

  const onSubmit = ({ current_password, new_password }: Values) =>
    change.mutate(
      { current_password, new_password },
      {
        onSuccess: () => {
          toast.success('Password changed')
          reset()
        },
        onError: (e) => toast.error(errorMessage(e)),
      },
    )

  return (
    <div className="max-w-xl space-y-6">
      <PageHeader title="Account" description="Your profile and sign-in details." />
      <Card>
        <CardHeader>
          <CardTitle>{me?.name ?? me?.email}</CardTitle>
          <CardDescription className="flex items-center gap-2">
            {me?.email}
            {me && (
              <Badge variant="secondary" className="capitalize">
                {me.role}
              </Badge>
            )}
          </CardDescription>
        </CardHeader>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
            <Field id="current_password" label="Current password" error={errors.current_password?.message}>
              <Input
                id="current_password"
                type="password"
                autoComplete="current-password"
                {...register('current_password')}
              />
            </Field>
            <Field id="new_password" label="New password" error={errors.new_password?.message}>
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                {...register('new_password')}
              />
            </Field>
            <Field id="confirm" label="Repeat new password" error={errors.confirm?.message}>
              <Input id="confirm" type="password" autoComplete="new-password" {...register('confirm')} />
            </Field>
            <Button type="submit" className="justify-self-start" disabled={change.isPending}>
              {change.isPending && <Loader2 className="animate-spin" aria-hidden />}
              Change password
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
