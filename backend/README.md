# Issue Reporting & Intervention System — Backend

Generic intake → queue → assignment → field intervention → status updates → history →
notifications platform. All niche-specific behaviour lives behind a **domain adapter**,
so the business domain can be swapped without touching the schema, services or routers.

Current status: **intake, queue, workflow transitions, assignment, notifications and
JWT authentication with role-based authorization (Phase 1–6)**. No frontend yet.

## Stack

Python 3.13 · FastAPI · SQLAlchemy 2.x · Alembic · PostgreSQL 17 (psycopg 3) · Pydantic v2 · pytest

## Architecture

```text
React (later)
     |  REST + Authorization: Bearer <JWT>
     v
Authentication           who is the user?        app/auth/dependencies.py
     |
     v
Authorization            may they do this?       app/auth/dependencies.py + access.py
     |
     v
  FastAPI routers          thin, no business logic
     |
     +--------------------------+
     |                          |
     v                          v
Domain adapter          Application services
(all niche rules)       (transactions, history, orchestration)
                               |
                               v
                          SQLAlchemy  ->  PostgreSQL
```

Each layer answers exactly one question, and the domain adapter knows nothing about
tokens or roles: valid transitions, issue types and worker scoring stay pure domain
rules, while "who is calling" and "may they" are settled before a service is called.

### Layout

```text
backend/
├── app/
│   ├── main.py                 FastAPI app, error handlers, /health
│   ├── auth/
│   │   ├── security.py         password hashing + JWT encode/decode
│   │   ├── schemas.py          register/login/token payloads
│   │   ├── service.py          registration and credential checking
│   │   ├── dependencies.py     get_current_user, require_roles
│   │   ├── access.py           per-resource ownership checks
│   │   └── router.py           /auth/register, /auth/login, /auth/me
│   ├── core/
│   │   ├── config.py           pydantic-settings, reads .env
│   │   ├── database.py         engine, session factory, Base, get_db
│   │   ├── enums.py            roles, priorities, statuses, actions
│   │   └── errors.py           AppError family -> HTTP status codes
│   ├── domain/
│   │   ├── base.py             DomainAdapter contract + worker scoring
│   │   ├── current.py          ACTIVE domain (Generic Intervention)
│   │   └── examples.py         Municipal Maintenance reference adapter
│   ├── models/                 users, tickets, ticket_history, assignments, notifications
│   ├── schemas/                Pydantic request/response models
│   ├── services/               business logic + transactions
│   │   ├── ticket_service.py       intake, queue, status transitions
│   │   ├── assignment_service.py   dispatch, acceptance, workers, recommendations
│   │   ├── history_service.py      ticket timeline writer
│   │   └── notification_service.py in-app notification fan-out
│   └── routers/                tickets, assignments, workers, notifications, domain
├── alembic/                    migration environment + versions
├── scripts/seed.py             development users to log in as
├── tests/
├── docker-compose.yml          PostgreSQL 17
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Setup

All commands run from `backend/`.

```bash
# 1. Configuration
cp .env.example .env

# 2. Database
docker compose up -d

# 3. Dependencies (uv)
uv venv
uv pip install -r requirements.txt

#    ...or plain pip
python -m venv .venv
.venv/Scripts/activate      # Windows
pip install -r requirements.txt

# 4. Schema
alembic upgrade head

# 5. Development users to log in as
python -m scripts.seed

# 6. Run
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs.

On Windows PowerShell, prefix commands with the interpreter if the venv is not
activated, e.g. `.\.venv\Scripts\python.exe -m alembic upgrade head`.

## Database commands

```bash
alembic upgrade head                              # apply migrations
alembic downgrade -1                              # roll back one migration
alembic revision --autogenerate -m "description"  # create a migration from model changes
alembic current                                   # show applied revision
```

## Tests

```bash
pytest -q
```

The suite creates `intervention_test_db` automatically and truncates the core
tables between tests, so it never touches the development database.

## Authentication

Stateless JWT bearer tokens. Passwords are hashed with Argon2 (via `pwdlib`, falling
back to bcrypt if the extra is missing) and never leave the API: no response schema
exposes `password_hash`.

```text
POST /auth/login  ->  {"access_token": "...", "token_type": "bearer"}
                          |
                          v
           Authorization: Bearer <token>  on every other request
                          |
                          v
              get_current_user()  ->  current_user.id / .role
```

The token carries `sub` (user id), `role` and `exp`. The `role` claim is informational
— useful for laying out a UI — but **every authorization decision re-reads the role
from the database**, so changing or revoking a role takes effect immediately rather
than when the token expires. A token claiming `ADMIN` for a reporter's id gets a `403`.

### Login example

```bash
# OAuth2 password flow (form-encoded); this is what the /docs Authorize button uses
curl -X POST http://localhost:8000/auth/token \
  -d "username=dispatcher@example.com" \
  -d "password=Dispatcher123!"

# Or the JSON variant the frontend will use
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "dispatcher@example.com", "password": "Dispatcher123!"}'
```

Then send the token on every request:

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <TOKEN>"

curl -X POST http://localhost:8000/tickets \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Street light out on 42B", "type": "OUTAGE", "priority": "HIGH"}'
```

### Registration

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Ahmed", "email": "ahmed@example.com",
       "password": "password123", "role": "CONTRACTOR"}'
```

Self-registration accepts `REPORTER` and `CONTRACTOR` only. `DISPATCHER` and `ADMIN`
are refused with `422` and come from the seed script or administrative provisioning,
so nobody can grant themselves dispatch or full access.

> Public self-registration is itself a hackathon simplification; a real deployment
> would put invitations or email verification in front of it.

### Development credentials

Created by `python -m scripts.seed`. **Development only** — they are published here so
the team can sign in locally, and must never exist in a deployed environment. The
script refuses to run unless `ENVIRONMENT` is `development`, `local` or `test`.

| Role       | Email                     | Password         |
| ---------- | ------------------------- | ---------------- |
| ADMIN      | `admin@example.com`       | `Admin123!`      |
| DISPATCHER | `dispatcher@example.com`  | `Dispatcher123!` |
| CONTRACTOR | `contractor1@example.com` | `Contractor123!` |
| CONTRACTOR | `contractor2@example.com` | `Contractor123!` |
| REPORTER   | `reporter@example.com`    | `Reporter123!`   |

`JWT_SECRET_KEY` in `.env` is likewise a development placeholder. Generate a real one
with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Roles and permissions

`ADMIN` may do everything; the table lists the other three.

| Action                             | REPORTER   | CONTRACTOR       | DISPATCHER |
| ---------------------------------- | ---------- | ---------------- | ---------- |
| Create a ticket                    | yes        | yes              | yes        |
| List tickets                       | own only   | assigned only    | all        |
| View one ticket / its history      | own only   | assigned only    | all        |
| See worker recommendations         | no         | no               | yes        |
| Assign / reassign                  | no         | no               | yes        |
| Accept an assignment               | no         | own job only     | no         |
| Start work / resolve               | no         | own job only     | no         |
| Close a resolved ticket            | no         | no               | yes        |
| List all workers                   | no         | no               | yes        |
| Read a worker's jobs               | no         | own only         | any worker |
| Read / mark notifications          | own only   | own only         | own only   |

Two kinds of check are enforced, and both live outside the endpoints themselves:

- **Role** — `require_roles("DISPATCHER")`, a dependency, so an endpoint either has the
  gate or it does not; there are no ad-hoc role comparisons scattered through routers.
- **Ownership** — `app/auth/access.py`, because it needs the resource as well as the
  user. Contractor A calling `start` on contractor B's job gets `403`, whatever the
  frontend chose to render.

Notification ownership is strict for everyone, administrators included: `/notifications`
only ever returns the caller's own inbox.

## API

Everything except `/health` and `/auth/*` requires `Authorization: Bearer <token>`.

| Method | Path                            | Who                | Notes                                            |
| ------ | ------------------------------- | ------------------ | ------------------------------------------------ |
| GET    | `/health`                       | public             | Liveness plus database and active-domain status  |
| POST   | `/auth/register`                | public             | Self-registration (REPORTER / CONTRACTOR only)   |
| POST   | `/auth/login`                   | public             | JSON credentials -> access token                 |
| POST   | `/auth/token`                   | public             | Same, form-encoded, for the /docs Authorize button |
| GET    | `/auth/me`                      | any                | The signed-in user                               |
| POST   | `/tickets`                      | any                | Report an issue; reporter is the caller          |
| GET    | `/tickets`                      | any                | Queue, scoped to the caller's role               |
| GET    | `/tickets/{id}`                 | reporter/worker/staff | Single ticket, including the assigned worker  |
| PATCH  | `/tickets/{id}/status`          | depends on target  | Move through the workflow                        |
| GET    | `/tickets/{id}/history`         | reporter/worker/staff | Timeline, oldest first                        |
| GET    | `/tickets/{id}/recommendations` | dispatcher, admin  | Ranked worker suggestions                        |
| POST   | `/tickets/{id}/assign`          | dispatcher, admin  | Dispatch to a worker                             |
| POST   | `/tickets/{id}/accept`          | assigned worker    | Worker accepts the job                           |
| GET    | `/workers`                      | dispatcher, admin  | Workers with skills, availability, workload      |
| GET    | `/workers/me`                   | contractor         | Your own worker profile                          |
| GET    | `/workers/me/tickets`           | contractor         | Your own jobs (`?active_only=true`)              |
| GET    | `/workers/{id}/tickets`         | self or staff      | That worker's jobs (`?active_only=true`)         |
| GET    | `/notifications`                | any                | Your inbox (`?unread_only=true`)                 |
| GET    | `/notifications/unread-count`   | any                | How many of yours are unread                     |
| PATCH  | `/notifications/{id}/read`      | owner              | Mark one of yours as read                        |
| GET    | `/domain/config`                | public             | Terminology, issue types, transitions, skills    |
| GET    | `/domain/issue-types`           | public             | Issue types accepted by the active domain        |

`GET /tickets` accepts `status`, `priority`, `type`, `reporter_id`, `limit`, `offset`
and orders by priority (CRITICAL first), then oldest first. The `reporter_id` filter
only widens anything for a dispatcher or admin: a reporter always sees their own
reports and a contractor their own jobs, whatever the query string asks for.

### Error responses

| Status | Meaning                                                         |
| ------ | --------------------------------------------------------------- |
| 401    | Missing, malformed, forged or expired token                     |
| 403    | Authenticated, but the role or ownership rule refuses the action |
| 404    | No such ticket, user or notification                            |
| 409    | The workflow refuses the move (invalid or duplicate transition) |
| 422    | Payload or domain validation failed                             |

Authentication failures are deliberately uninformative: a wrong email and a wrong
password give the same `401 Incorrect email or password.`, and login spends the same
time either way, so the endpoint cannot be used to discover which addresses exist.

### Status transitions

`PATCH /tickets/{id}/status` takes `{"status": ..., "comment": ...}` and, in a single
transaction: validates the move against the adapter, updates the ticket, stamps the
active assignment's `started_at`/`completed_at`, writes a `ticket_history` entry, and
notifies the reporter, the assigned worker, and — once a ticket is `RESOLVED` — every
dispatcher. Whoever performed the action is never notified about it.

The actor is the authenticated caller. There is no `actor_id` field any more: the
timeline records who really did it, and a client cannot act in someone else's name.

Who may attempt which move:

| Target        | Allowed callers                       |
| ------------- | ------------------------------------- |
| `IN_PROGRESS` | the contractor holding the assignment |
| `RESOLVED`    | the contractor holding the assignment |
| `CLOSED`      | dispatcher, admin                     |

Rejected moves answer `409`, e.g.
`{"detail": "Cannot move a ticket from ASSIGNED to CLOSED. Allowed from ASSIGNED: IN_PROGRESS."}`.
`OPEN → ASSIGNED` is deliberately refused here — even for a dispatcher — because it
must go through the assign endpoint so an `assignments` row always exists.

### Assignment

`POST /tickets/{id}/assign` takes `{"contractor_id": ..., "notes": ...}` from a
dispatcher or admin — `assigned_by` is the authenticated caller — and, in one
transaction, inserts an `assignments` row, moves an `OPEN` ticket to
`ASSIGNED`, writes history, and notifies the worker, the reporter, and anyone
replaced. Rules worth knowing:

- Assignment is allowed while a ticket is `OPEN` or `ASSIGNED`. Assigning an already
  `ASSIGNED` ticket is a **reassignment**: it appends a row (never overwrites) and
  leaves the status alone, so every dispatch attempt stays auditable. "Who is on this
  job" is always the newest row.
- `IN_PROGRESS`, `RESOLVED` and `CLOSED` tickets refuse assignment with `409`.
- Only users whose role is `CONTRACTOR` can be assigned (`422` otherwise). A skill
  mismatch does **not** block assignment; the dispatcher may override, and
  `/recommendations` surfaces the mismatch.
- `POST /tickets/{id}/accept` takes no body: the caller is the worker. It stamps
  `accepted_at` and records `ASSIGNMENT_ACCEPTED` without changing status. Only the
  assigned worker may accept — a different contractor gets `403`. Starting work
  implies acceptance, so `accepted_at` is filled in either way.

`GET /tickets/{id}/recommendations` returns deterministic suggestions, ranked by the
adapter (skill 50, availability 25, distance 15, workload 10) with the reasoning
attached, for example:

```json
[{ "worker_id": "...", "name": "Sami Sparks", "score": 100,
   "reasons": ["Required skill matched: ELECTRICAL", "Currently available",
               "0.1 km from the site", "No open jobs"] }]
```

Errors always use a single human-readable string:

```json
{ "detail": "Unknown issue type 'SPACESHIP'. Expected one of: GENERAL, EQUIPMENT, DAMAGE, OUTAGE." }
```

## Swapping the domain

`app/domain/current.py` is the only file that has to change. Either edit
`CurrentDomainAdapter` or point `ACTIVE_DOMAIN` at another adapter:

```python
from app.domain.examples import MunicipalMaintenanceAdapter

ACTIVE_DOMAIN: DomainAdapter = MunicipalMaintenanceAdapter()
```

An adapter defines the domain name, issue types, worker label, skill vocabulary,
status transitions, required metadata per issue type, the skills each issue type
needs, and (optionally) how workers are ranked. Because niche-specific ticket
fields live in the `tickets.metadata` JSONB column and worker skills in
`users.skills` JSONB, no migration is needed to change domain.

Worker recommendation is deterministic (no ML), weighted: skill match 50,
availability 25, distance 15, workload 10.

## Notes

- UUID primary keys, UTC (`timestamptz`) timestamps everywhere.
- `Ticket.meta` is the Python attribute for the `metadata` column, because
  `metadata` is reserved on SQLAlchemy's declarative base. The API field is
  `metadata`.
- Every meaningful ticket action writes a `ticket_history` row inside the same
  transaction as the change itself.
- Reassignment inserts a new `assignments` row rather than overwriting, keeping
  dispatch history intact.
- Email addresses are validated on write only. Response schemas use plain strings,
  so one unusual stored address cannot break a whole listing.
- Service dependencies point one way — `ticket_service` → `assignment_service` →
  `history_service` / `notification_service` — so notifications never query
  assignments. Callers pass in whoever is involved.
- `users.password_hash` is nullable: imported or seeded rows may exist without a
  password, and such an account simply cannot log in.
- Tokens are stateless, so there is no logout endpoint and no revocation list. A
  token stays valid until it expires (12 hours by default,
  `ACCESS_TOKEN_EXPIRE_MINUTES`); a role change, however, applies immediately,
  because roles are read from the database on every request.

## Tooling

```bash
ruff check app tests scripts   # lint
pytest -q                      # tests
alembic check                  # schema drift
```

## The client

The React UI lives in [`../frontend`](../frontend/README.md) and consumes this API
exactly as described above: it stores the access token, sends
`Authorization: Bearer <token>` with every request, and never sends an actor id.
It hides controls a role cannot use, but treats that purely as courtesy — every
rule above is enforced here, server-side, and its end-to-end test walks a ticket
through the whole workflow to prove the two agree.
