import { zodResolver } from '@hookform/resolvers/zod'
import { Bug, Loader2 } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { z } from 'zod'

import { Field } from '@/components/common/Field'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ApiError, errorMessage } from '@/lib/api/errors'

import { useCurrentUser, useLogin } from '../api/queries'
import { safeNext } from '../lib/safeNext'

const schema = z.object({
  email: z.string().trim().min(1, 'Enter your email'),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

export function LoginPage() {
  const { data: me, isPending } = useCurrentUser()
  const login = useLogin()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))
  const { register, handleSubmit, formState } = useForm<Values>({ resolver: zodResolver(schema) })
  const { errors } = formState

  if (!isPending && me) return <Navigate to={next} replace />

  const onSubmit = (values: Values) =>
    login.mutate(values, { onSuccess: () => void navigate(next, { replace: true }) })

  return (
    <main className="bg-muted/30 flex min-h-dvh items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex items-center justify-center gap-2 font-semibold">
          <span className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-md">
            <Bug className="size-4" aria-hidden />
          </span>
          Ticket Intake
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
            <CardDescription>Use the account your workspace admin created for you.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
              <Field id="email" label="Email" error={errors.email?.message}>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  autoFocus
                  aria-invalid={errors.email ? true : undefined}
                  {...register('email')}
                />
              </Field>
              <Field id="password" label="Password" error={errors.password?.message}>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={errors.password ? true : undefined}
                  {...register('password')}
                />
              </Field>
              {login.isError && (
                <p role="alert" className="text-destructive text-sm">
                  {login.error instanceof ApiError && login.error.status === 404
                    ? 'This deployment signs you in through the workspace platform, not here.'
                    : errorMessage(login.error)}
                </p>
              )}
              <Button type="submit" disabled={login.isPending}>
                {login.isPending && <Loader2 className="animate-spin" aria-hidden />}
                Sign in
              </Button>
            </form>
          </CardContent>
        </Card>
        {import.meta.env.DEV && (
          <p className="text-muted-foreground text-center text-xs">
            Local demo, after <code>make seed</code>: adam@example.com / adam-demo-password (admin);
            tara@example.com (triager), alice@example.com and bob@example.com (members) / demo-password.
          </p>
        )}
      </div>
    </main>
  )
}
