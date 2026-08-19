# Intervention System

Report an issue, dispatch it to the right person, and follow it through to
closure — with a full audit trail behind every step.

Someone reports a problem. A dispatcher sees it ranked by urgency, gets a shortlist
of workers scored on skills, availability, distance and current workload, and sends
it to one of them. That worker accepts it, starts it, and resolves it. The
dispatcher closes it. Everyone involved is notified as it moves, and every step is
recorded against the ticket.

```
REPORTER          DISPATCHER              CONTRACTOR            DISPATCHER
   │                   │                      │                     │
 report ──▶ OPEN ── assign ──▶ ASSIGNED ── accept/start ──▶ IN_PROGRESS
                                                  │                  │
                                              resolve ──▶ RESOLVED ─ close ──▶ CLOSED
```

## The two halves

| Part                             | What it is                                        |
| -------------------------------- | ------------------------------------------------- |
| [`backend/`](backend/README.md)  | FastAPI + PostgreSQL API, JWT auth, all the rules  |
| [`frontend/`](frontend/README.md) | React + TypeScript UI for all four roles          |

Start the API first, then the UI:

```bash
cd backend
alembic upgrade head
python -m scripts.seed          # development accounts to sign in with
uvicorn app.main:app --reload   # http://127.0.0.1:8000

cd ../frontend
npm install
npm run dev                     # http://localhost:5173
```

The sign-in screen offers one-click fills for the seeded accounts in development,
so you can switch between reporter, dispatcher, contractor and admin while trying
it out.

## Two ideas worth knowing

**The backend decides who you are.** Nothing on the client says which user is
acting: the API reads the identity from the bearer token and enforces every role
and ownership rule itself. The UI hides controls that would be refused, but that
is a courtesy to the user, never a security boundary.

**Nothing about the domain is hardcoded.** Issue types, priorities, statuses, the
skill vocabulary, the legal transitions and even the word "Contractor" come from a
domain adapter the API exposes at `GET /domain/config`. Pointing that adapter at
another niche — municipal maintenance, facilities, field service — re-labels and
re-options both halves without touching either codebase.

## Checks

```bash
cd backend  && pytest && ruff check .
cd frontend && npm run lint && npm run build && npm run test:e2e
```

The frontend's end-to-end test signs in as each role in turn and walks one ticket
from report to closure against the running API, so it fails the moment the UI and
the backend disagree about who may do what.
