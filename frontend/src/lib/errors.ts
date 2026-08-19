import { ApiError } from '@/api/client'

/**
 * Turns whatever a mutation threw into one sentence.
 *
 * A 403 is worth spelling out: it means the screen offered something the backend
 * refuses, which is a bug worth seeing rather than a silent no-op.
 */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.isForbidden
      ? `${error.message} (your role does not allow this action)`
      : error.message
  }
  if (error instanceof Error) return error.message

  return 'Something went wrong.'
}
