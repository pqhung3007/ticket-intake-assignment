import { Search, Users } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { toast } from 'sonner'

import { EmptyState } from '@/components/common/EmptyState'
import { ErrorState } from '@/components/common/ErrorState'
import { PageHeader } from '@/components/common/PageHeader'
import { PersonChip } from '@/components/common/PersonChip'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { errorMessage } from '@/lib/api/errors'
import type { User } from '@/lib/api/types'
import { timeAgo } from '@/lib/utils'

import { useSetRole, useUsers } from '../api/queries'

export function RolesPage() {
  const [search, setSearch] = useState('')
  const q = useDeferredValue(search.trim())
  const users = useUsers(q)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Roles"
        description="Triagers can change status, assign and edit any ticket, and see confidential tickets. Admins are set at deploy time."
      />
      <Card className="gap-0 py-0">
        <div className="border-b p-4">
          <div className="relative max-w-sm">
            <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" aria-hidden />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or email"
              className="pl-8"
              aria-label="Search members"
            />
          </div>
        </div>
        <CardContent className="p-0">
          {users.isError ? (
            <div className="p-4">
              <ErrorState error={users.error} onRetry={() => void users.refetch()} />
            </div>
          ) : users.isPending ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : users.data.items.length === 0 ? (
            <div className="p-4">
              <EmptyState
                icon={Users}
                title="No members found"
                description="Members appear here after they open the app for the first time."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Member</TableHead>
                  <TableHead>Last seen</TableHead>
                  <TableHead className="w-48 pr-4">Role</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.data.items.map((user) => (
                  <RoleRow key={user.id} user={user} />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function RoleRow({ user }: { user: User }) {
  const setRole = useSetRole()
  const onChange = (role: string) =>
    setRole.mutate(
      { userId: user.id, role: role as 'member' | 'triager' },
      {
        onSuccess: (u) => toast.success(`${u.name ?? u.email ?? 'User'} is now a ${u.role}`),
        onError: (e) => toast.error(errorMessage(e)),
      },
    )

  return (
    <TableRow>
      <TableCell className="pl-4">
        <div className="flex flex-col">
          <PersonChip name={user.name} email={user.email} />
          {user.email && <span className="text-muted-foreground pl-8 text-xs">{user.email}</span>}
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground">{timeAgo(user.last_seen_at)}</TableCell>
      <TableCell className="pr-4">
        {user.role_source === 'config' ? (
          <Badge variant="secondary">Admin (deployment)</Badge>
        ) : (
          <Select value={user.role} onValueChange={onChange} disabled={setRole.isPending}>
            <SelectTrigger size="sm" className="w-36" aria-label={`Role for ${user.name ?? user.id}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="member">Member</SelectItem>
              <SelectItem value="triager">Triager</SelectItem>
            </SelectContent>
          </Select>
        )}
      </TableCell>
    </TableRow>
  )
}
