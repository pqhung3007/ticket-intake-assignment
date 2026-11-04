import type { Severity, Status } from '@/lib/api/types'

export const SEVERITIES: readonly Severity[] = ['critical', 'high', 'medium', 'low']
export const STATUSES: readonly Status[] = ['open', 'in_progress', 'resolved', 'closed']

export const SEVERITY_META: Record<Severity, { label: string; description: string; className: string }> = {
  critical: {
    label: 'Critical',
    description: 'Outage, data loss or security issue',
    className: 'bg-sev-critical/12 text-sev-critical border-sev-critical/30',
  },
  high: {
    label: 'High',
    description: 'A main feature is unusable',
    className: 'bg-sev-high/12 text-sev-high border-sev-high/30',
  },
  medium: {
    label: 'Medium',
    description: 'Degraded, but a workaround exists',
    className: 'bg-sev-medium/12 text-sev-medium border-sev-medium/30',
  },
  low: {
    label: 'Low',
    description: 'Cosmetic or minor inconvenience',
    className: 'bg-sev-low/12 text-sev-low border-sev-low/30',
  },
}

export const STATUS_META: Record<Status, { label: string; className: string; dot: string }> = {
  open: { label: 'Open', className: 'text-st-open border-st-open/30 bg-st-open/10', dot: 'bg-st-open' },
  in_progress: {
    label: 'In progress',
    className: 'text-st-progress border-st-progress/30 bg-st-progress/10',
    dot: 'bg-st-progress',
  },
  resolved: {
    label: 'Resolved',
    className: 'text-st-resolved border-st-resolved/30 bg-st-resolved/10',
    dot: 'bg-st-resolved',
  },
  closed: {
    label: 'Closed',
    className: 'text-st-closed border-st-closed/30 bg-st-closed/10',
    dot: 'bg-st-closed',
  },
}

export const FIELD_LABELS: Record<string, string> = {
  title: 'title',
  description: 'description',
  steps_to_reproduce: 'steps to reproduce',
  expected_behavior: 'expected behaviour',
  actual_behavior: 'actual behaviour',
  environment: 'environment',
  severity: 'severity',
  target_app: 'app',
  confidential: 'confidentiality',
}
