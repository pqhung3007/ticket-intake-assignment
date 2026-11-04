import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, UserPlus } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { Field } from '@/components/common/Field'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { errorMessage } from '@/lib/api/errors'

import { useCreateUser } from '../api/queries'

const schema = z.object({
  name: z.string().trim().min(1, 'Enter a name').max(100),
  email: z.email('Enter a valid email'),
  password: z.string().min(10, 'Use at least 10 characters').max(200),
})
type Values = z.infer<typeof schema>

export function CreateUserDialog() {
  const [open, setOpen] = useState(false)
  const create = useCreateUser()
  const { register, handleSubmit, reset, formState } = useForm<Values>({ resolver: zodResolver(schema) })
  const { errors } = formState

  const onSubmit = (values: Values) =>
    create.mutate(values, {
      onSuccess: (user) => {
        toast.success(`Created ${user.name ?? user.email}`, {
          description: 'Share the initial password with them; they can change it under Account.',
        })
        reset()
        setOpen(false)
      },
      onError: (e) => toast.error(errorMessage(e)),
    })

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) {
          reset()
          create.reset()
        }
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <UserPlus aria-hidden />
          Add member
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a member</DialogTitle>
          <DialogDescription>
            They sign in with this email and password. New accounts are members; promote them to triager from
            the list.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
          <Field id="name" label="Name" error={errors.name?.message}>
            <Input id="name" autoComplete="off" {...register('name')} />
          </Field>
          <Field id="new-email" label="Email" error={errors.email?.message}>
            <Input id="new-email" type="email" autoComplete="off" {...register('email')} />
          </Field>
          <Field
            id="new-password"
            label="Initial password"
            error={errors.password?.message}
            hint="At least 10 characters."
          >
            <Input id="new-password" type="password" autoComplete="new-password" {...register('password')} />
          </Field>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending && <Loader2 className="animate-spin" aria-hidden />}
            Create account
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
