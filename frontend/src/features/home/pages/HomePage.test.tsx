import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Me } from '@/lib/api/types'

import { HomePage } from './HomePage'

let me: Me | null = null
vi.mock('@/features/auth', () => ({ useCurrentUser: () => ({ data: me }) }))
vi.mock('@/features/tickets', () => ({
  StatsCards: () => <div>status-cards</div>,
  TicketPanel: ({ title }: { title: string }) => <section>{title}</section>,
}))

const user = (role: Me['role']): Me => ({
  id: 'u1',
  email: 'x@example.com',
  name: 'Sam Example',
  role,
  is_triager: role !== 'member',
  is_admin: role === 'admin',
  agent_id: null,
})

const renderHome = () =>
  render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )

describe('HomePage', () => {
  beforeEach(() => {
    me = null
  })

  it('shows members their own reports', () => {
    me = user('member')
    renderHome()
    expect(screen.getByRole('heading', { name: 'Hi Sam' })).toBeInTheDocument()
    expect(screen.getByText('Your reports')).toBeInTheDocument()
    expect(screen.queryByText('Needs triage')).not.toBeInTheDocument()
  })

  it('shows triagers a work queue', () => {
    me = user('triager')
    renderHome()
    expect(screen.getByRole('heading', { name: 'Triage queue' })).toBeInTheDocument()
    expect(screen.getByText('Assigned to you')).toBeInTheDocument()
    expect(screen.queryByText('Manage members')).not.toBeInTheDocument()
  })

  it('shows admins an overview with member management', () => {
    me = user('admin')
    renderHome()
    expect(screen.getByRole('heading', { name: 'Workspace overview' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /manage members/i })).toHaveAttribute('href', '/admin/roles')
  })
})
