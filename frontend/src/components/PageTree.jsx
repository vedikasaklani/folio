import { useEffect, useState } from 'react'
import { api } from '../api'
import { fieldErrors } from '../lib/errors'
import { keyOf } from '../lib/pageTree'
import Alert from './ui/Alert'
import Button from './ui/Button'
import IconButton from './ui/IconButton'
import { ChevronRight, Plus, Trash2 } from './ui/icons'
import './PageTree.css'

// One tree level: loads its first batch on mount, "Load more" follows the cursor.
function Level({ parent, ctx }) {
  const level = ctx.tree.levels[keyOf(parent)]
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const fail = (err) => setError(fieldErrors(err).form ?? 'Could not load pages.')

  async function load() {
    setBusy(true)
    setError(null)
    await ctx.load(parent).catch(fail)
    setBusy(false)
  }

  useEffect(() => {
    if (!level) ctx.load(parent).catch(fail) // first load only; later loads are explicit
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <>
      <ul className="tree__level">
        {level?.ids.map((id) => (
          <Node key={id} id={id} ctx={ctx} />
        ))}
      </ul>
      {error && <Alert>{error}</Alert>}
      {level?.next || error ? (
        <Button variant="ghost" size="xs" loading={busy} onClick={load} className="tree__more">
          {error ? 'Retry' : 'Load more'}
        </Button>
      ) : (
        !level && <p className="t-caption t-muted tree__hint">Loading…</p>
      )}
      {level && !level.ids.length && parent === null && <p className="t-caption t-muted tree__hint">No pages yet.</p>}
    </>
  )
}

function Node({ id, ctx }) {
  const page = ctx.tree.pages[id]
  const [open, setOpen] = useState(false)

  async function addChild() {
    if (await ctx.add(id)) setOpen(true)
  }

  return (
    <li>
      <div className={`tree__row${ctx.selectedId === id ? ' is-selected' : ''}`}>
        {page.has_children ? (
          <button
            type="button"
            className="tree__chevron"
            aria-expanded={open}
            aria-label={`${open ? 'Collapse' : 'Expand'} ${page.name}`}
            onClick={() => setOpen(!open)}
          >
            <ChevronRight aria-hidden="true" className={open ? 'is-open' : ''} />
          </button>
        ) : (
          <span className="tree__chevron" aria-hidden="true" />
        )}
        <button
          type="button"
          className="tree__name"
          aria-current={ctx.selectedId === id || undefined}
          onClick={() => ctx.onSelect(id)}
        >
          {page.name}
        </button>
        {ctx.canWrite && (
          <span className="tree__actions">
            <button type="button" aria-label={`Add page inside ${page.name}`} onClick={addChild}>
              <Plus aria-hidden="true" />
            </button>
            <button type="button" aria-label={`Delete ${page.name}`} onClick={() => ctx.remove(id)}>
              <Trash2 aria-hidden="true" />
            </button>
          </span>
        )}
      </div>
      {open && <Level parent={id} ctx={ctx} />}
    </li>
  )
}

// collapsed = the sidebar is an icon rail. The tree stays mounted (just hidden), so nothing refetches on expand.
export default function PageTree({ workspaceId, tree, dispatch, selectedId, onSelect, canWrite, collapsed }) {
  const [error, setError] = useState(null)

  async function load(parent) {
    const level = tree.levels[keyOf(parent)]
    const url = level?.next ?? `/api/pages/?workspace=${workspaceId}&parent=${parent ?? 'null'}`
    const data = await api(url)
    dispatch({ type: 'loaded', parent, results: data.results, next: data.next })
  }

  // New pages are created untitled and opened in the editor, where they get a name. Returns true on success.
  async function add(parent = null) {
    setError(null)
    try {
      const { id, name } = await api('/api/pages/', { method: 'POST', body: { workspace: workspaceId, name: 'Untitled', parent } })
      dispatch({ type: 'added', page: { id, parent, name, has_children: false } })
      onSelect(id)
      return true
    } catch (err) {
      setError(fieldErrors(err).form ?? 'Could not create the page.')
      return false
    }
  }

  async function remove(id) {
    const page = tree.pages[id]
    const what = page.has_children ? `"${page.name}" and every page inside it` : `"${page.name}"`
    if (!window.confirm(`Delete ${what}? This cannot be undone.`)) return
    setError(null)
    try {
      await api(`/api/pages/${id}/`, { method: 'DELETE' })
      dispatch({ type: 'removed', id })
    } catch (err) {
      setError(fieldErrors(err).form ?? 'Could not delete the page.')
    }
  }

  const ctx = { tree, load, add, remove, selectedId, onSelect, canWrite }
  return (
    <nav className="tree" aria-label="Pages">
      <div className="tree__head">
        {collapsed ? null : <h2 className="t-label t-muted">Pages</h2>}
        {canWrite ? (
          collapsed ? (
            <IconButton icon={Plus} label="New page" onClick={() => add(null)} />
          ) : (
            <Button variant="soft" size="xs" icon={Plus} onClick={() => add(null)}>
              New page
            </Button>
          )
        ) : null}
      </div>
      <div className="tree__body" hidden={collapsed} inert={collapsed}>
        {error ? <Alert>{error}</Alert> : null}
        <Level parent={null} ctx={ctx} />
      </div>
    </nav>
  )
}
