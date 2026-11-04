import { useQueryClient } from '@tanstack/react-query'
import { FlaskConical } from 'lucide-react'
import { useState } from 'react'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DEV_USERS, env } from '@/config/env'
import { DEV_USER_STORAGE_KEY } from '@/lib/api/client'
import { safeStorage } from '@/lib/storage'

/** Local development only: switch between fixed identities to exercise each role. */
export function DevUserSwitcher() {
  const queryClient = useQueryClient()
  const [user, setUser] = useState(() => safeStorage.get(DEV_USER_STORAGE_KEY) ?? 'alice')
  if (!env.devAuth) return null

  const onChange = (next: string) => {
    safeStorage.set(DEV_USER_STORAGE_KEY, next)
    setUser(next)
    void queryClient.resetQueries()
  }

  return (
    <div className="flex items-center gap-2">
      <FlaskConical className="text-muted-foreground size-4" aria-hidden />
      <Select value={user} onValueChange={onChange}>
        <SelectTrigger size="sm" aria-label="Development identity">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DEV_USERS.map((u) => (
            <SelectItem key={u.key} value={u.key}>
              {u.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
