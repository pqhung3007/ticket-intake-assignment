/** Friendly aliases for generated API schema types. Never edit schema.gen.ts by hand. */
import type { components } from './schema.gen'

type Schemas = components['schemas']

export type Me = Schemas['MeOut']
export type Role = Schemas['Role']
export type User = Schemas['UserOut']
export type Severity = Schemas['Severity']
export type Status = Schemas['Status']
export type Ticket = Schemas['TicketOut']
export type TicketSummary = Schemas['TicketSummaryOut']
export type TicketEvent = Schemas['TicketEventOut']
export type TicketDetail = Schemas['TicketDetailOut']
export type TicketPermissions = Schemas['TicketPermissionsOut']
export type TicketList = Schemas['TicketListOut']
export type TicketStats = Schemas['TicketStatsOut']
export type TicketCreateInput = Schemas['TicketCreateIn']
export type TicketUpdateInput = Schemas['TicketUpdateIn']
