/**
 * The single place the browser talks to the API.
 *
 * Every request carries the bearer token, and the backend derives the acting user
 * from it: no screen ever sends an actor id, because the client is not trusted to
 * say who it is.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

const TOKEN_KEY = 'intervention.access_token'

/** Fires when a request comes back 401, so the app can drop to the login screen. */
type UnauthorizedHandler = () => void

let onUnauthorized: UnauthorizedHandler = () => {}

export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  onUnauthorized = handler
}

export function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    // Private-mode browsers can refuse storage; the session just will not persist.
    return null
  }
}

export function writeToken(token: string | null): void {
  try {
    if (token === null) localStorage.removeItem(TOKEN_KEY)
    else localStorage.setItem(TOKEN_KEY, token)
  } catch {
    /* ignore: an unpersisted session still works until the tab is closed */
  }
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }

  /** The caller is signed in but not allowed to do this. */
  get isForbidden(): boolean {
    return this.status === 403
  }

  get isNotFound(): boolean {
    return this.status === 404
  }

  /** The workflow refused the move, e.g. RESOLVED before IN_PROGRESS. */
  get isConflict(): boolean {
    return this.status === 409
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  /** Sent form-encoded, as the OAuth2 password flow requires. */
  form?: Record<string, string>
  query?: Record<string, string | number | boolean | undefined | null>
  /** Login and registration are the only calls made without a token. */
  anonymous?: boolean
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, form, query, anonymous = false } = options

  const headers = new Headers()
  const token = anonymous ? null : readToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let payload: BodyInit | undefined
  if (form) {
    headers.set('Content-Type', 'application/x-www-form-urlencoded')
    payload = new URLSearchParams(form).toString()
  } else if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
    payload = JSON.stringify(body)
  }

  const response = await fetch(`${BASE_URL}${path}${buildQuery(query)}`, {
    method,
    headers,
    body: payload,
  })

  if (response.status === 401 && !anonymous) onUnauthorized()

  if (!response.ok) throw new ApiError(response.status, await readError(response))

  if (response.status === 204) return undefined as T

  return (await response.json()) as T
}

function buildQuery(query: RequestOptions['query']): string {
  if (!query) return ''

  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    params.set(key, String(value))
  }
  const serialised = params.toString()

  return serialised ? `?${serialised}` : ''
}

/** The API always answers with `{"detail": "..."}`; fall back if it ever does not. */
async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    /* fall through to the generic message below */
  }

  return response.status === 401
    ? 'Your session has expired. Please sign in again.'
    : `Request failed (${response.status}).`
}
