import { initials } from './utils'

describe('initials', () => {
  it.each([
    ['Alice Member', 'AM'],
    ['alice', 'A'],
    ['Mary Jane Watson', 'MW'],
    [null, '?'],
    ['   ', '?'],
  ])('%s -> %s', (name, expected) => {
    expect(initials(name)).toBe(expected)
  })
})
