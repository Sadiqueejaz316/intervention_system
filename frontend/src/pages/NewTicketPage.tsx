import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import type { TicketPriority } from '@/api/types'
import { Alert, Button, ButtonLink, PageHeader } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { classes } from '@/lib/format'
import { useCreateTicket, useDomainConfig } from '@/hooks/queries'

export function NewTicketPage() {
  const navigate = useNavigate()
  const { data: config } = useDomainConfig()
  const createTicket = useCreateTicket()

  const [chosenType, setChosenType] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('MEDIUM')
  const [building, setBuilding] = useState('')
  const [elevatorId, setElevatorId] = useState('')
  const [floor, setFloor] = useState('')
  const [people, setPeople] = useState('1')
  const [communication, setCommunication] = useState<'yes' | 'no' | ''>('')
  const [locationText, setLocationText] = useState('')

  const issueTypes = config?.issue_types ?? []
  const emergencyType = config?.metadata_hint.emergency_type ?? 'PERSON_TRAPPED'
  const buildings = config?.metadata_hint.buildings ?? []
  const elevators = config?.metadata_hint.elevator_ids ?? []
  const type = chosenType ?? ''
  const isEmergency = type === emergencyType
  const selectedIssue = issueTypes.find((item) => item.value === type)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!type) return

    const metadata: Record<string, unknown> = {}
    if (building) metadata.building_name = building
    if (elevatorId) metadata.elevator_id = elevatorId
    if (floor.trim()) metadata.floor = Number(floor) || floor.trim()
    if (isEmergency) {
      metadata.people_trapped = Number(people) || 1
      if (communication) metadata.communication_possible = communication === 'yes'
    }

    const buildingAddress = buildings.find((item) => item.name === building)?.address
    if (buildingAddress) metadata.building_address = buildingAddress

    createTicket.mutate(
      {
        title:
          title.trim() ||
          selectedIssue?.label ||
          'Elevator incident',
        description: description.trim() || null,
        type,
        priority: isEmergency ? 'CRITICAL' : priority,
        location_text: locationText.trim() || null,
        metadata,
      },
      { onSuccess: (ticket) => void navigate(`/tickets/${ticket.id}`) },
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Report an elevator incident"
        subtitle="Say what's wrong. If anyone is trapped, that report jumps the queue."
        action={
          <ButtonLink to="/tickets" variant="secondary">
            Cancel
          </ButtonLink>
        }
      />

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {createTicket.isError && <Alert>{errorMessage(createTicket.error)}</Alert>}

        <fieldset className="card space-y-3 p-5">
          <legend className="text-base font-medium text-ink">
            What's wrong with the elevator?
          </legend>
          <div className="grid gap-2">
            {issueTypes.map((issue) => (
              <label
                key={issue.value}
                className={classes(
                  'flex cursor-pointer gap-3 rounded-lg border p-3 transition',
                  issue.emergency && 'border-red-300 bg-red-50',
                  type === issue.value && issue.emergency && 'ring-2 ring-red-500',
                  type === issue.value && !issue.emergency && 'border-brand-500 bg-brand-50',
                  type !== issue.value && !issue.emergency && 'border-line hover:bg-canvas',
                )}
              >
                <input
                  type="radio"
                  name="issue-type"
                  className="mt-1 accent-red-600"
                  checked={type === issue.value}
                  onChange={() => setChosenType(issue.value)}
                />
                <span>
                  <span className="block text-sm font-semibold text-ink">
                    {issue.emergency ? `🚨 ${issue.label.toUpperCase()}` : issue.label}
                  </span>
                  {issue.description && (
                    <span className="block text-xs text-muted">{issue.description}</span>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        {type && (
          <div className="card space-y-5 p-6">
            {isEmergency && (
              <Alert tone="error">
                This is an emergency. Priority is locked to CRITICAL. Give the
                dispatcher a building, elevator and a headcount if you can — don't
                delay the report for missing details.
              </Alert>
            )}

            {isEmergency && (
              <div>
                <span className="label">Are people trapped inside the elevator?</span>
                <p className="text-sm font-medium text-red-800">Yes — that's why this is an emergency.</p>
              </div>
            )}

            {isEmergency && (
              <div>
                <label className="label" htmlFor="people">
                  How many people?
                </label>
                <input
                  id="people"
                  className="input w-32"
                  type="number"
                  min={1}
                  required
                  value={people}
                  onChange={(event) => setPeople(event.target.value)}
                />
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="building">
                  Which building?
                </label>
                <select
                  id="building"
                  className="input"
                  value={building}
                  onChange={(event) => setBuilding(event.target.value)}
                >
                  <option value="">Not sure yet</option>
                  {buildings.map((item) => (
                    <option key={item.name} value={item.name}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="elevator">
                  Which elevator?
                </label>
                <select
                  id="elevator"
                  className="input"
                  value={elevatorId}
                  onChange={(event) => setElevatorId(event.target.value)}
                >
                  <option value="">Not sure yet</option>
                  {elevators.map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="label" htmlFor="floor">
                Known floor?
              </label>
              <input
                id="floor"
                className="input w-32"
                inputMode="numeric"
                value={floor}
                onChange={(event) => setFloor(event.target.value)}
                placeholder="7"
              />
            </div>

            {isEmergency && (
              <fieldset>
                <legend className="label">Can you communicate with people inside?</legend>
                <div className="flex gap-3">
                  {(['yes', 'no'] as const).map((value) => (
                    <label key={value} className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="communication"
                        checked={communication === value}
                        onChange={() => setCommunication(value)}
                      />
                      {value === 'yes' ? 'Yes' : 'No'}
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            {!isEmergency && (
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
                      {value}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label className="label" htmlFor="title">
                Short summary <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                id="title"
                className="input"
                minLength={3}
                maxLength={255}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder={selectedIssue?.label}
              />
            </div>

            <div>
              <label className="label" htmlFor="description">
                Additional information{' '}
                <span className="font-normal text-muted">(optional)</span>
              </label>
              <textarea
                id="description"
                className="input min-h-24 resize-y"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Anything that helps the technician on arrival."
              />
            </div>

            <div>
              <label className="label" htmlFor="location">
                Extra location notes{' '}
                <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                id="location"
                className="input"
                value={locationText}
                onChange={(event) => setLocationText(event.target.value)}
                placeholder="Lobby entrance, service key at reception"
              />
            </div>

            <div className="flex justify-end gap-2 border-t border-line pt-4">
              <ButtonLink to="/tickets" variant="secondary">
                Cancel
              </ButtonLink>
              <Button type="submit" loading={createTicket.isPending}>
                {isEmergency ? 'Submit emergency' : 'Submit report'}
              </Button>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}
