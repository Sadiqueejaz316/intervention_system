"""Seed the development database with elevator-service accounts and demo tickets.

DEVELOPMENT ONLY. The passwords below are published in the README so the team can
sign in during the hackathon; never run this against anything but a local database.

    python -m scripts.seed          # insert what is missing, refresh names/skills
    python -m scripts.seed --reset  # reset the seeded accounts' passwords too

Dispatchers and administrators exist only here: `/auth/register` deliberately
refuses those roles, so this script is the provisioning path for them.
"""

import argparse
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import TicketPriority, TicketStatus, UserRole
from app.domain.current import get_domain_adapter
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.assignment import AssignmentCreate
from app.schemas.ticket import TicketCreate, TicketStatusUpdate
from app.services import assignment_service, ticket_service

#: name, email, role, password, skills, latitude, longitude, available
SeedUser = tuple[
    str, str, UserRole, str, list[str], float | None, float | None, bool
]

SEED_USERS: list[SeedUser] = [
    (
        "Amina Admin",
        "admin@example.com",
        UserRole.ADMIN,
        "Admin123!",
        [],
        None,
        None,
        True,
    ),
    (
        "Dalia Dispatcher",
        "dispatcher@example.com",
        UserRole.DISPATCHER,
        "Dispatcher123!",
        [],
        None,
        None,
        True,
    ),
    (
        "Ahmed Khan",
        "contractor1@example.com",
        UserRole.CONTRACTOR,
        "Contractor123!",
        ["ELEVATOR_GENERAL", "ELEVATOR_EMERGENCY", "DOOR_SYSTEM"],
        36.8065,
        10.1815,
        True,
    ),
    (
        "Sami Sparks",
        "contractor2@example.com",
        UserRole.CONTRACTOR,
        "Contractor123!",
        ["ELEVATOR_GENERAL", "ELEVATOR_EMERGENCY", "ELECTRICAL"],
        36.8090,
        10.1840,
        True,
    ),
    (
        "Farid Faraway",
        "farid@example.com",
        UserRole.CONTRACTOR,
        "Contractor123!",
        ["ELEVATOR_GENERAL"],
        36.5000,
        10.8000,
        False,
    ),
    (
        "Rania Reporter",
        "reporter@example.com",
        UserRole.REPORTER,
        "Reporter123!",
        [],
        None,
        None,
        True,
    ),
]


def seed(db: Session, *, reset_passwords: bool) -> dict[str, User]:
    by_email: dict[str, User] = {}

    for name, email, role, password, skills, latitude, longitude, available in SEED_USERS:
        existing = db.execute(
            select(User).where(func.lower(User.email) == email)
        ).scalars().first()

        if existing is not None:
            existing.name = name
            existing.role = role.value
            existing.skills = skills
            existing.latitude = latitude
            existing.longitude = longitude
            existing.is_available = available
            if reset_passwords:
                existing.password_hash = hash_password(password)
                print(f"  updated+reset  {email}")
            else:
                print(f"  updated         {email}")
            by_email[email] = existing
            continue

        user = User(
            name=name,
            email=email,
            role=role.value,
            password_hash=hash_password(password),
            skills=skills,
            latitude=latitude,
            longitude=longitude,
            is_available=available,
        )
        db.add(user)
        print(f"  created         {email:28} {role.value}")
        by_email[email] = user

    db.commit()
    for user in by_email.values():
        db.refresh(user)

    _seed_demo_tickets(db, by_email)
    return by_email


def _seed_demo_tickets(db: Session, users: dict[str, User]) -> None:
    already = db.execute(
        select(func.count(Ticket.id)).where(Ticket.type == "PERSON_TRAPPED")
    ).scalar_one()
    if already:
        print("  elevator demo incidents already present — skipping")
        return

    adapter = get_domain_adapter()
    reporter = users["reporter@example.com"]
    dispatcher = users["dispatcher@example.com"]
    ahmed = users["contractor1@example.com"]
    sami = users["contractor2@example.com"]

    trapped = ticket_service.create_ticket(
        db,
        TicketCreate(
            title="People trapped in elevator",
            description="Two residents are trapped inside. Alarm was pressed.",
            type="PERSON_TRAPPED",
            priority=TicketPriority.LOW,
            metadata={
                "building_name": "Building A",
                "building_address": "12 Rue de la Liberte, Tunis",
                "elevator_id": "ELV-02",
                "floor": 7,
                "cabin_number": "C-02",
                "people_trapped": 2,
                "communication_possible": True,
                "additional_details": "Can hear voices; cabin lights are on.",
            },
        ),
        adapter,
        reporter_id=reporter.id,
    )
    print(f"  incident        PERSON_TRAPPED {trapped.id} CRITICAL OPEN")

    outage = ticket_service.create_ticket(
        db,
        TicketCreate(
            title="Elevator out of service",
            description="ELV-01 has been dark since this morning.",
            type="ELEVATOR_OUT_OF_SERVICE",
            priority=TicketPriority.HIGH,
            metadata={
                "building_name": "Building B",
                "elevator_id": "ELV-01",
                "floor": 0,
            },
        ),
        adapter,
        reporter_id=reporter.id,
    )
    print(f"  incident        OUT_OF_SERVICE {outage.id} HIGH OPEN")

    door = ticket_service.create_ticket(
        db,
        TicketCreate(
            title="Landing doors not closing",
            description="Doors reverse on every close attempt.",
            type="DOOR_MALFUNCTION",
            priority=TicketPriority.HIGH,
            metadata={
                "building_name": "Building C",
                "elevator_id": "ELV-04",
                "door_state": "OPEN",
            },
        ),
        adapter,
        reporter_id=reporter.id,
    )
    assignment_service.assign_ticket(
        db,
        door.id,
        AssignmentCreate(contractor_id=ahmed.id, notes="Check the door operator."),
        adapter,
        actor=dispatcher,
    )
    print(f"  incident        DOOR_MALFUNCTION {door.id} HIGH ASSIGNED")

    noise = ticket_service.create_ticket(
        db,
        TicketCreate(
            title="Grinding noise in the shaft",
            description="Residents on floors 3–5 reported it overnight.",
            type="ABNORMAL_NOISE",
            priority=TicketPriority.MEDIUM,
            metadata={
                "building_name": "Building D",
                "elevator_id": "ELV-03",
            },
        ),
        adapter,
        reporter_id=reporter.id,
    )
    assignment_service.assign_ticket(
        db,
        noise.id,
        AssignmentCreate(contractor_id=sami.id),
        adapter,
        actor=dispatcher,
    )
    assignment_service.accept_assignment(db, noise.id, adapter, actor=sami)
    ticket_service.change_status(
        db,
        noise.id,
        TicketStatusUpdate(
            status=TicketStatus.IN_PROGRESS, comment="On site, inspecting."
        ),
        adapter,
        actor_id=sami.id,
    )
    print(f"  incident        ABNORMAL_NOISE {noise.id} MEDIUM IN_PROGRESS")

    lighting = ticket_service.create_ticket(
        db,
        TicketCreate(
            title="Cabin lighting failure",
            description="ELV-01 cabin is dark; landings are fine.",
            type="LIGHTING_FAILURE",
            priority=TicketPriority.LOW,
            metadata={
                "building_name": "Building B",
                "elevator_id": "ELV-01",
            },
        ),
        adapter,
        reporter_id=reporter.id,
    )
    assignment_service.assign_ticket(
        db,
        lighting.id,
        AssignmentCreate(contractor_id=sami.id),
        adapter,
        actor=dispatcher,
    )
    assignment_service.accept_assignment(db, lighting.id, adapter, actor=sami)
    ticket_service.change_status(
        db,
        lighting.id,
        TicketStatusUpdate(status=TicketStatus.IN_PROGRESS),
        adapter,
        actor_id=sami.id,
    )
    ticket_service.change_status(
        db,
        lighting.id,
        TicketStatusUpdate(status=TicketStatus.RESOLVED, comment="Replaced cabin lamps."),
        adapter,
        actor_id=sami.id,
    )
    print(f"  incident        LIGHTING_FAILURE {lighting.id} LOW RESOLVED")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="reset the password of accounts that already exist",
    )
    args = parser.parse_args()

    if settings.ENVIRONMENT.lower() not in {"development", "local", "test"}:
        print(
            f"Refusing to seed: ENVIRONMENT is '{settings.ENVIRONMENT}'. "
            f"These are development-only credentials.",
            file=sys.stderr,
        )
        return 1

    print(f"Seeding {settings.DATABASE_URL.rsplit('/', 1)[-1]}")

    with SessionLocal() as db:
        seed(db, reset_passwords=args.reset)

    print("\nDevelopment credentials (never use these outside development):")
    for name, email, role, password, *_ in SEED_USERS:
        print(f"  {role.value:11} {email:28} {password:16} {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
