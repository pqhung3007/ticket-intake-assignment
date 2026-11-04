import { emptyTicketForm, ticketFormSchema, toTicketPayload } from './schemas'

describe('ticket form schema', () => {
  it('requires a title and app', () => {
    const result = ticketFormSchema.safeParse(emptyTicketForm)
    expect(result.success).toBe(false)
    const fields = result.error?.issues.map((i) => i.path[0])
    expect(fields).toEqual(expect.arrayContaining(['title', 'target_app']))
  })

  it('accepts a minimal valid report', () => {
    expect(
      ticketFormSchema.safeParse({ ...emptyTicketForm, title: 'Export fails', target_app: 'reports' })
        .success,
    ).toBe(true)
  })

  it('sends blank optional fields as null', () => {
    const payload = toTicketPayload({ ...emptyTicketForm, title: 'Bug', target_app: 'x', environment: '   ' })
    expect(payload.environment).toBeNull()
    expect(payload.steps_to_reproduce).toBeNull()
    expect(payload.description).toBe('')
  })
})
