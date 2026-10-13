import { useEffect, useState } from 'react'
import { api } from '../api'
import { fieldErrors } from '../lib/errors'
import DocEditor from './DocEditor'
import Alert from './ui/Alert'

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
  return <DocEditor page={page} canWrite={canWrite} onSaved={onSaved} />
}
