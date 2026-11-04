import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { errorMessage } from '@/lib/api/errors'

import { useAddComment } from '../api/mutations'

export function CommentForm({ number }: { number: number }) {
  const [body, setBody] = useState('')
  const addComment = useAddComment(number)
  const trimmed = body.trim()

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!trimmed) return
    addComment.mutate(trimmed, {
      onSuccess: () => setBody(''),
      onError: (err) => toast.error(errorMessage(err)),
    })
  }

  return (
    <form onSubmit={submit} className="grid gap-2">
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(e)
        }}
        placeholder="Add a comment… (⌘/Ctrl + Enter to send)"
        aria-label="Comment"
        maxLength={5000}
        rows={3}
      />
      <div className="flex justify-end">
        <Button type="submit" size="sm" disabled={!trimmed || addComment.isPending}>
          {addComment.isPending && <Loader2 className="animate-spin" aria-hidden />}
          Comment
        </Button>
      </div>
    </form>
  )
}
