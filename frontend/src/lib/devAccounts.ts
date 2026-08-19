/**
 * Seeded development logins, offered as one-click fills on the sign-in screen.
 *
 * Only rendered under `import.meta.env.DEV`, so they never reach a production
 * bundle. They match `backend/scripts/seed.py`.
 */
export const DEV_ACCOUNTS = [
  { label: 'Reporter', email: 'reporter@example.com', password: 'Reporter123!' },
  { label: 'Dispatcher', email: 'dispatcher@example.com', password: 'Dispatcher123!' },
  { label: 'Contractor', email: 'contractor1@example.com', password: 'Contractor123!' },
  { label: 'Admin', email: 'admin@example.com', password: 'Admin123!' },
]
