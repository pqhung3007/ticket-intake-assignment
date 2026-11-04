/** Where to go after signing in. Only same-app paths are allowed, so a crafted link can't redirect off-site. */
export function safeNext(next: string | null): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) return '/'
  return next.startsWith('/login') ? '/' : next
}
