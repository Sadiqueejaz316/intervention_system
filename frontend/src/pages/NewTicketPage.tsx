import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import type { TicketPriority } from '@/api/types'
import { Alert, Button, ButtonLink, PageHeader } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { classes, humanise } from '@/lib/format'
import { useCreateTicket, useDomainConfig } from '@/hooks/queries'

export function NewTicketPage() {
  const navigate = useNavigate()
  const { data: config } = useDomainConfig()
  const createTicket = useCreateTicket()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [chosenType, setChosenType] = useState<string | null>(null)
  const [priority, setPriority] = useState<TicketPriority>('MEDIUM')
  const [locationText, setLocationText] = useState('')
  const [coordinates, setCoordinates] = useState<{ lat: number; lon: number } | null>(
    null,
  )
  const [locating, setLocating] = useState(false)

  // The adapter owns the issue vocabulary, so the default is whatever it lists
  // first — derived rather than stored, so it is right on the very first render.
  const type = chosenType ?? config?.issue_types[0] ?? ''
  const requiredSkills = config?.required_skills_by_type[type] ?? []

  function locateMe() {
    if (!navigator.geolocation) return
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoordinates({
          lat: Number(position.coords.latitude.toFixed(5)),
          lon: Number(position.coords.longitude.toFixed(5)),
        })
        setLocating(false)
      },
      () => setLocating(false),
      { timeout: 8000 },
    )
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()

    createTicket.mutate(
      {
        title: title.trim(),
        description: description.trim() || null,
        type,
        priority,
        location_text: locationText.trim() || null,
        latitude: coordinates?.lat ?? null,
        longitude: coordinates?.lon ?? null,
      },
      { onSuccess: (ticket) => void navigate(`/tickets/${ticket.id}`) },
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Report an issue"
        subtitle="You are recorded as the reporter; the dispatcher takes it from here."
        action={
          <ButtonLink to="/tickets" variant="secondary">
            Cancel
          </ButtonLink>
        }
      />

      <form onSubmit={handleSubmit} className="card space-y-5 p-6" noValidate>
        {createTicket.isError && <Alert>{errorMessage(createTicket.error)}</Alert>}

        <div>
          <label className="label" htmlFor="title">
            What is wrong?
          </label>
          <input
            id="title"
            className="input"
            required
            minLength={3}
            maxLength={255}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Street light out on 42B"
          />
        </div>

        <div>
          <label className="label" htmlFor="description">
            Details <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id="description"
            className="input min-h-24 resize-y"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Anything that helps whoever shows up."
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="type">
              Type
            </label>
            <select
              id="type"
              className="input"
              value={type}
              onChange={(event) => setChosenType(event.target.value)}
            >
              {(config?.issue_types ?? []).map((value) => (
                <option key={value} value={value}>
                  {humanise(value)}
                </option>
              ))}
            </select>
            {requiredSkills.length > 0 && (
              <p className="mt-1.5 text-xs text-muted">
                Usually handled by: {requiredSkills.map(humanise).join(', ')}
              </p>
            )}
          </div>

          <div>
            <span className="label">Priority</span>
            <div className="flex flex-wrap gap-1.5">
              {(config?.priorities ?? []).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setPriority(value)}
                  aria-pressed={priority === value}
                  className={classes(
                    'rounded-md px-2.5 py-1.5 text-xs font-medium ring-1 ring-inset transition',
                    priority === value
                      ? 'bg-brand-600 text-white ring-brand-600'
                      : 'bg-canvas text-muted ring-line hover:text-ink',
                  )}
                >
                  {humanise(value)}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div>
          <label className="label" htmlFor="location">
            Where <span className="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="location"
            className="input"
            maxLength={500}
            value={locationText}
            onChange={(event) => setLocationText(event.target.value)}
            placeholder="Avenue Habib Bourguiba, near the pharmacy"
          />
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              loading={locating}
              onClick={locateMe}
            >
              Use my location
            </Button>
            {coordinates && (
              <span className="text-xs text-muted">
                {coordinates.lat}, {coordinates.lon} — used to suggest the nearest
                worker
              </span>
            )}
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <ButtonLink to="/tickets" variant="secondary">
            Cancel
          </ButtonLink>
          <Button type="submit" loading={createTicket.isPending}>
            Submit report
          </Button>
        </div>
      </form>
    </div>
  )
}
