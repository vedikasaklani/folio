import { lazy, Suspense, useEffect, useState } from 'react'
import { api } from '../api'
import { fieldErrors } from '../lib/errors'
import Alert from './ui/Alert'

// The editor (TipTap + syntax highlighting) is the heaviest code in the app: load it when the first page opens,
// not for the login screen or the workspace pane.
const DocEditor = lazy(() => import('./DocEditor'))

// Mount with key={pageId}: switching pages remounts and refetches. The list rows have no body, so it loads here.
export default function PageEditor({ pageId, canWrite, onSaved }) {
  const [page, setPage] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let stale = false
    api(`/api/pages/${pageId}/`)
      .then((p) => !stale && setPage(p))
      .catch((err) => !stale && setError(fieldErrors(err).form ?? 'Could not load the page.'))
    return () => {
      stale = true
    }
  }, [pageId])

  if (error) return <Alert>{error}</Alert>
  if (!page) return <p className="t-body t-muted">Loading…</p>
  return (
    <Suspense fallback={<p className="t-body t-muted">Loading…</p>}>
      <DocEditor page={page} canWrite={canWrite} onSaved={onSaved} />
    </Suspense>
  )
}
