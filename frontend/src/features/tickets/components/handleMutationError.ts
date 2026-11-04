import { toast } from 'sonner'

import { ApiError, errorMessage } from '@/lib/api/errors'

/** Consistent feedback for failed ticket writes. */
export function handleMutationError(error: unknown) {
  if (error instanceof ApiError && error.code === 'version_conflict') {
    toast.warning('Someone else just changed this ticket', {
      description: 'The latest version has been loaded. Please review and try again.',
    })
    return
  }
  toast.error(errorMessage(error))
}
