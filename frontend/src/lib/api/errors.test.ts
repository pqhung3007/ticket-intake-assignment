import { ApiError, errorMessage } from './errors'

describe('ApiError', () => {
  it('maps validation details to field errors', () => {
    const err = new ApiError(400, 'validation_error', 'Invalid', [
      { field: 'title', message: 'too short' },
      { field: 'target_app', message: 'required' },
    ])
    expect(err.fieldErrors).toEqual({ title: 'too short', target_app: 'required' })
  })

  it('has no field errors for other codes', () => {
    expect(new ApiError(409, 'version_conflict', 'Stale').fieldErrors).toEqual({})
  })

  it('flags conflicts', () => {
    expect(new ApiError(409, 'version_conflict', 'Stale').isConflict).toBe(true)
  })

  it('produces a readable message for any error', () => {
    expect(errorMessage(new ApiError(403, 'forbidden', 'Nope'))).toBe('Nope')
    expect(errorMessage('weird')).toBe('Something went wrong')
  })
})
