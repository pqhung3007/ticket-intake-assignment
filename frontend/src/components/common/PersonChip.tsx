import { Bot } from 'lucide-react'

import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn, initials } from '@/lib/utils'

export function PersonChip({
  name,
  email,
  agent,
  className,
}: {
  name: string | null | undefined
  email?: string | null
  agent?: string | null
  className?: string
}) {
  const label = name || email || 'Unknown'
  return (
    <span className={cn('inline-flex min-w-0 items-center gap-2', className)}>
      <Avatar className="size-6">
        <AvatarFallback className="text-[10px]">{initials(label)}</AvatarFallback>
      </Avatar>
      <span className="truncate" title={email ?? undefined}>
        {label}
      </span>
      {agent && (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="bg-muted text-muted-foreground inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs">
              <Bot className="size-3" aria-hidden />
              via agent
            </span>
          </TooltipTrigger>
          <TooltipContent>
            Done by agent “{agent}” on {label}&apos;s behalf
          </TooltipContent>
        </Tooltip>
      )}
    </span>
  )
}
