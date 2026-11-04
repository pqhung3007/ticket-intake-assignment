import { Label } from '@/components/ui/label'

/** Label + control + hint/error, wired for accessibility (aria-describedby set by the caller via ids). */
export function Field({
  id,
  label,
  hint,
  error,
  optional,
  children,
}: {
  id: string
  label: string
  hint?: React.ReactNode
  error?: string
  optional?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>
        {label}
        {optional && <span className="text-muted-foreground text-xs font-normal">optional</span>}
      </Label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-destructive text-sm">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="text-muted-foreground text-xs">
            {hint}
          </p>
        )
      )}
    </div>
  )
}
