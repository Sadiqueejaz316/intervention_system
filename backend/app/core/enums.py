from enum import StrEnum


class UserRole(StrEnum):
    REPORTER = "REPORTER"
    DISPATCHER = "DISPATCHER"
    CONTRACTOR = "CONTRACTOR"
    ADMIN = "ADMIN"


class TicketPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class HistoryAction(StrEnum):
    TICKET_CREATED = "TICKET_CREATED"
    TICKET_UPDATED = "TICKET_UPDATED"
    PRIORITY_CHANGED = "PRIORITY_CHANGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    ASSIGNED = "ASSIGNED"
    ASSIGNMENT_ACCEPTED = "ASSIGNMENT_ACCEPTED"
    WORK_STARTED = "WORK_STARTED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    COMMENT_ADDED = "COMMENT_ADDED"


class NotificationType(StrEnum):
    INFO = "INFO"
    ASSIGNMENT = "ASSIGNMENT"
    STATUS_CHANGE = "STATUS_CHANGE"
    ESCALATION = "ESCALATION"


# Lower value sorts first: the dispatcher queue leads with CRITICAL work.
PRIORITY_RANK: dict[str, int] = {
    TicketPriority.CRITICAL: 0,
    TicketPriority.HIGH: 1,
    TicketPriority.MEDIUM: 2,
    TicketPriority.LOW: 3,
}
