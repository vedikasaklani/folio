import { useState } from 'react'
import { api } from '../api'
import Alert from '../components/ui/Alert'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { Field } from '../components/ui/Field'
import { LogOut, Plus, Users } from '../components/ui/icons'
import { fieldErrors } from '../lib/errors'
import { ROLE_LABEL } from '../lib/roles'
import { workspaceTone } from '../lib/tone'
import './WorkspacePane.css'

const MAX_CHIPS = 4

// All cards are the same size and carry the workspace's own theme colour.
// lead = the workspace you were last in: it comes first and is labelled.
function WorkspaceCard({ workspace, tone, lead, onPick }) {
  const others = workspace.members.filter((m) => !m.is_you)
  return (
    <Card as="li" variant="tint" tone={tone} className="ws-card">
      {lead ? <p className="t-caption">Last opened</p> : null}
      <div className="ws-card__top">
        <button type="button" className="ws-card__open t-heading" onClick={() => onPick(workspace.id)}>
          {workspace.name}
        </button>
        <Badge>{ROLE_LABEL[workspace.role]}</Badge>
      </div>
      {workspace.description ? <p className="t-body ws-card__desc">{workspace.description}</p> : null}
      <div className="ws-card__members">
        <p className="t-caption">
          <Users aria-hidden="true" /> {others.length ? `${others.length + 1} members` : 'Just you'}
        </p>
        {others.length > 0 ? (
          <ul className="ws-card__chips" aria-label="Other members">
            {others.slice(0, MAX_CHIPS).map((m) => (
              <li key={m.username}>
                <Badge>{m.username}</Badge>
              </li>
            ))}
            {others.length > MAX_CHIPS ? (
              <li>
                <Badge>+{others.length - MAX_CHIPS}</Badge>
              </li>
            ) : null}
          </ul>
        ) : null}
      </div>
    </Card>
  )
}

function NewWorkspaceCard({ onCreated }) {
  const [open, setOpen] = useState(false)
  const [values, setValues] = useState({ name: '', description: '' })
  const [errors, setErrors] = useState({})
  const [pending, setPending] = useState(false)

  function handleChange(e) {
    const { name, value } = e.target
    setValues((v) => ({ ...v, [name]: value }))
    setErrors(({ [name]: _fixed, ...rest }) => rest)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    setPending(true)
    try {
      onCreated(await api('/api/workspaces/', { method: 'POST', body: values }))
    } catch (err) {
      setErrors(fieldErrors(err))
      setPending(false)
    }
  }

  if (!open) {
    return (
      <li className="ws-card ws-card--new">
        <button type="button" className="ws-card__new t-heading" onClick={() => setOpen(true)}>
          <Plus aria-hidden="true" /> New workspace
        </button>
      </li>
    )
  }
  return (
    <Card as="li" className="ws-card ws-card--form">
      <form className="ws-card__form" onSubmit={handleSubmit} noValidate>
        {errors.form ? <Alert>{errors.form}</Alert> : null}
        <Field label="Name" name="name" value={values.name} onChange={handleChange} error={errors.name} autoFocus required />
        <Field label="Description" name="description" value={values.description} onChange={handleChange} error={errors.description} />
        <div className="ws-card__actions">
          <Button type="submit" size="sm" loading={pending}>
            Create
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  )
}

export default function WorkspacePane({ workspaces, leadId, onPick, onCreated, onSignOut }) {
  const lead = workspaces.find((w) => w.id === leadId)
  const ordered = lead ? [lead, ...workspaces.filter((w) => w !== lead)] : workspaces
  return (
    <main className="pane">
      <header className="pane__head">
        <p className="pane__logo">folio</p>
        <Button variant="ghost" size="xs" icon={LogOut} onClick={onSignOut}>
          Sign out
        </Button>
      </header>
      <h1 className="t-title">Your workspaces</h1>
      <ul className="pane__grid">
        {ordered.map((w) => (
          <WorkspaceCard key={w.id} workspace={w} tone={workspaceTone(workspaces, w)} lead={w === lead} onPick={onPick} />
        ))}
        <NewWorkspaceCard onCreated={onCreated} />
      </ul>
    </main>
  )
}
