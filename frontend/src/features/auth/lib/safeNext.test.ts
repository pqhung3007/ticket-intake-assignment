import { describe, expect, it } from 'vitest'

import { safeNext } from './safeNext'

describe('safeNext', () => {
  it('keeps same-app paths, including query strings', () => {
    expect(safeNext('/tickets/7?tab=activity')).toBe('/tickets/7?tab=activity')
  })

  it.each([
    null,
    '',
    'https://evil.test',
    '//evil.test',
    '/\\evil.test',
    'tickets',
    '/login',
    '/login?next=/x',
  ])('falls back to home for %j', (value) => {
    expect(safeNext(value)).toBe('/')
  })
})
