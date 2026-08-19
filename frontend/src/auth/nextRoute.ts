const DEFAULT_ROUTE = '/tickets'

/**
 * Where to land after signing in, from `?next=`.
 *
 * Only in-app paths are honoured. `//evil.example` is a protocol-relative URL, so
 * it is rejected too — otherwise the sign-in screen would be a redirector to
 * anywhere on the internet.
 */
export function nextRoute(search: string): string {
  const target = new URLSearchParams(search).get('next')

  if (!target?.startsWith('/') || target.startsWith('//')) return DEFAULT_ROUTE

  return target
}
