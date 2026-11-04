/** Typed access to build-time configuration. */
export const env = {
  /** Local development only: send fixed dev identities instead of relying on the platform session. */
  devAuth: import.meta.env.VITE_DEV_AUTH === 'true',
} as const

export const DEV_USERS = [
  { key: 'alice', label: 'Alice (member)' },
  { key: 'bob', label: 'Bob (member)' },
  { key: 'tara', label: 'Tara (triager)' },
  { key: 'adam', label: 'Adam (admin)' },
] as const
