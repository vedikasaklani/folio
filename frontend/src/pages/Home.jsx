import { useEffect, useState } from 'react'
import { api } from '../api'
import Alert from '../components/ui/Alert'
import { fieldErrors } from '../lib/errors'
import { workspaceTone } from '../lib/tone'
import WorkspacePane from './WorkspacePane'
import WorkspaceView from './WorkspaceView'

const LAST_KEY = 'folio_workspace'

// Signed-in screen: the workspace pane (cards) until one is picked, then the workspace itself.
export default function Home({ onSignOut }) {
  const [workspaces, setWorkspaces] = useState(null)
  const [lastId, setLastId] = useState(() => Number(localStorage.getItem(LAST_KEY)) || null) // the lead card in the pane
  const [inWorkspace, setInWorkspace] = useState(lastId !== null) // false = showing the pane
  const [error, setError] = useState(null)

  useEffect(() => {
    api('/api/workspaces/')
      .then(setWorkspaces)
      .catch((err) => (err.status === 401 ? onSignOut() : setError(fieldErrors(err).form)))
  }, [onSignOut])

  function pick(id) {
    localStorage.setItem(LAST_KEY, id)
    setLastId(id)
    setInWorkspace(true)
  }

  if (error) return <Alert>{error}</Alert>
  if (!workspaces) return <p className="t-body t-muted" style={{ padding: 'var(--s-4)' }}>Loading…</p>

  const current = inWorkspace ? workspaces.find((w) => w.id === lastId) : null
  return current ? (
    <WorkspaceView
      key={current.id}
      workspace={current}
      tone={workspaceTone(workspaces, current)}
      onSwitch={() => setInWorkspace(false)}
      onSignOut={onSignOut}
    />
  ) : (
    <WorkspacePane
      workspaces={workspaces}
      leadId={lastId}
      onPick={pick}
      onCreated={(w) => {
        setWorkspaces([...workspaces, w])
        pick(w.id)
      }}
      onSignOut={onSignOut}
    />
  )
}
