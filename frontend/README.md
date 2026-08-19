# Intervention System — Web UI

React front end for the intervention API: report an issue, dispatch it to the
right worker, and follow it through to closure.

## Status

Complete for the four roles the API supports. Sign-in, the ticket queue, ticket
creation, the full `OPEN → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED` workflow,
dispatcher recommendations, the worker directory and notifications are all wired
to the live backend.

## Stack

| Concern     | Choice                | Why                                                     |
| ----------- | --------------------- | ------------------------------------------------------- |
| Build       | Vite + React + TS     | Fast dev server, typed against the API schemas          |
| Routing     | React Router          | Nested layout route with per-role guards                |
| Server data | TanStack Query        | Caching plus one place to invalidate after a transition |
| Styling     | Tailwind CSS v4       | Themed in `src/index.css`, no config file needed        |

## Setup

The API must be running first — see [`../backend/README.md`](../backend/README.md).
Seed the development accounts with `python -m scripts.seed` so you can sign in.

```bash
npm install
npm run dev          # http://localhost:5173
```

Requests go to `/api/*`, which the Vite dev server proxies to
`http://127.0.0.1:8000`. Only one origin is involved, so CORS never enters the
picture in development.

| Variable         | Default                 | Purpose                                        |
| ---------------- | ----------------------- | ---------------------------------------------- |
| `VITE_API_PROXY` | `http://127.0.0.1:8000` | Where the dev proxy forwards `/api`            |
| `VITE_API_URL`   | _(unset)_               | Absolute API origin, for a deployed build      |

For a production build, point the app straight at the API and skip the proxy:

```bash
VITE_API_URL=https://api.example.com npm run build
npm run preview
```

## Signing in

In development the sign-in screen offers one-click fills for the seeded accounts
(reporter, dispatcher, contractor, admin). They are wrapped in
`import.meta.env.DEV`, so they are dropped from a production bundle. Anyone can
self-register as a reporter or a contractor; dispatcher and admin accounts come
from the seed script, exactly as the API allows.

The token is kept in `localStorage`. It is sent as `Authorization: Bearer …` on
every call, and any `401` clears the session and returns to sign-in — which is
also what happens when a token quietly expires in an open tab.

## What each role sees

| Screen              | Reporter        | Contractor          | Dispatcher / Admin |
| ------------------- | --------------- | ------------------- | ------------------ |
| Tickets             | Own reports     | Assigned jobs       | Everything         |
| Report an issue     | Yes             | Yes                 | Yes                |
| My jobs             | —               | Own queue           | —                  |
| Assign / recommend  | —               | —                   | Yes                |
| Accept a job        | —               | Own assignment      | —                  |
| Start / resolve     | —               | Own assignment      | Admin              |
| Close               | —               | —                   | Yes                |
| Workers             | —               | —                   | Yes                |
| Notifications       | Own             | Own                 | Own                |

The queue is not filtered in the browser: `GET /tickets` already returns only
what the caller may see, so each role gets a different list from the same call.

**These rules decide what to render, nothing more.** The API enforces the same
checks and is what actually protects the data; hiding a button is a courtesy, not
a security boundary. If the two ever disagree, the request comes back `403` and
the message is shown rather than swallowed, because that mismatch is a bug worth
seeing.

## Layout

```
src/
  api/          client.ts (fetch + token + errors), endpoints.ts, types.ts
  auth/         AuthProvider, context, useAuth, permissions
  components/   AppLayout, guards, ui primitives, TicketCard, AssignPanel, TicketTimeline
  hooks/        queries.ts — every useQuery/useMutation, with the cache keys
  lib/          formatting, error messages, seeded dev accounts
  pages/        Login, Register, Tickets, NewTicket, TicketDetail, MyJobs, Workers, Notifications
```

Two conventions are worth knowing before editing:

- **No screen sends an actor id.** The backend takes the acting user from the
  token, so `assign`, `accept` and status changes only carry the decision itself.
- **Nothing about the domain is hardcoded.** Issue types, priorities, statuses,
  the skill vocabulary, the legal transitions and even the word "Contractor" come
  from `GET /domain/config`. Repointing the backend adapter at another niche
  changes this UI's wording and options without a code change here.

## Workflow in the UI

Ticket detail offers only the moves the API would accept: the next statuses from
the domain adapter, narrowed to those the signed-in user may perform. `ASSIGNED`
is deliberately never offered as a status change — it comes from the assign
action, so an assignment record always exists.

A contractor sees "Accept this job", then "Start work", then "Mark resolved";
a dispatcher sees the ranked panel and, once resolved, "Close ticket".

The recommendation score is advice, not a gate. A skill mismatch is flagged but
never disables the button — the dispatcher knows things the ranking does not, and
the backend accepts the assignment either way.

## Checks

```bash
npm run lint         # oxlint
npm run build        # tsc -b && vite build
npm run test:e2e     # Playwright: full workflow against a running API
npm run screenshots  # refresh .screenshots/ for the docs
```

The end-to-end test signs in as each role in turn and walks a ticket from report
to closure, so it fails if the UI and the API ever drift apart. It needs both the
API and the seeded accounts; the dev server is started automatically.
