from enum import StrEnum


class Severity(StrEnum):
    LOW = "low"  # cosmetic, workaround is trivial
    MEDIUM = "medium"  # degraded, workaround exists
    HIGH = "high"  # a main feature is unusable
    CRITICAL = "critical"  # outage, data loss or security issue


class Status(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CreatedVia(StrEnum):
    UI = "ui"
    AGENT = "agent"


class EventType(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    COMMENT = "comment"


ACTIVE_STATUSES = frozenset({Status.OPEN, Status.IN_PROGRESS})
DONE_STATUSES = frozenset({Status.RESOLVED, Status.CLOSED})

# Fields a reporter/triager may edit. Identity and bookkeeping fields are never editable.
CONTENT_FIELDS = (
    "title",
    "description",
    "steps_to_reproduce",
    "expected_behavior",
    "actual_behavior",
    "environment",
    "severity",
    "target_app",
    "confidential",
)

# Window in which an identical keyless report from the same user is treated as a retry.
AUTO_DEDUPE_WINDOW_SECONDS = 10 * 60

MAX_EVENTS_PER_TICKET = 500
