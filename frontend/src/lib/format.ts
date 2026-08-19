export function classes(...values: (string | false | null | undefined)[]): string {
  return values.filter(Boolean).join(' ')
}

/** `IN_PROGRESS` -> `In progress`, so screaming enums stay out of the UI. */
export function humanise(value: string): string {
  const spaced = value.replace(/_/g, ' ').toLowerCase()

  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function formatRelative(value: string): string {
  const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000)

  // Each step is "how many of the current unit make one of the next".
  const steps: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, 'minute'],
    [60, 'hour'],
    [24, 'day'],
  ]

  let amount = seconds
  let unit: Intl.RelativeTimeFormatUnit = 'second'
  for (const [size, nextUnit] of steps) {
    if (Math.abs(amount) < size) break
    amount = Math.round(amount / size)
    unit = nextUnit
  }

  // Past a week "8 days ago" helps nobody; show the date instead.
  if (unit === 'day' && Math.abs(amount) >= 7) return formatDateTime(value)

  return new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }).format(
    -amount,
    unit,
  )
}
