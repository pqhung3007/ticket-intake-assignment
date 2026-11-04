import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { RequireAuth } from './RequireAuth'

let state: { data: unknown; isPending: boolean; isError: boolean } = {
  data: null,
  isPending: false,
  isError: false,
}
vi.mock('../api/queries', () => ({ useCurrentUser: () => state }))

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<div>login screen</div>} />
        <Route
          path="/tickets/:n"
          element={
            <RequireAuth>
              <div>secret</div>
            </RequireAuth>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireAuth', () => {
  it('sends signed-out visitors to the login screen', () => {
    state = { data: null, isPending: false, isError: false }
    renderAt('/tickets/3')
    expect(screen.getByText('login screen')).toBeInTheDocument()
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })

  it('renders children for a signed-in user', () => {
    state = { data: { id: 'u1' }, isPending: false, isError: false }
    renderAt('/tickets/3')
    expect(screen.getByText('secret')).toBeInTheDocument()
  })

  it('shows nothing protected while the session is being checked', () => {
    state = { data: undefined, isPending: true, isError: false }
    renderAt('/tickets/3')
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
    expect(screen.queryByText('login screen')).not.toBeInTheDocument()
  })
})
