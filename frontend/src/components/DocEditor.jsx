import { EditorContent, Node, useEditor } from '@tiptap/react'
import { Placeholder } from '@tiptap/extensions'
import StarterKit from '@tiptap/starter-kit'
import { useRef, useState } from 'react'
import { api } from '../api'
import { docFor } from '../lib/editorDoc'
import { fieldErrors } from '../lib/errors'
import { toneMarks } from '../lib/marks'
import EditorToolbar from './EditorToolbar'
import Alert from './ui/Alert'
import Badge from './ui/Badge'
import Button from './ui/Button'
import { Lock } from './ui/icons'
import './DocEditor.css'

// The page title is the document's first node, rendered as the h1. Plain text only; Enter moves on to a paragraph.
const Title = Node.create({
  name: 'title',
  content: 'text*',
  marks: '',
  defining: true,
  parseHTML: () => [{ tag: 'h1' }],
  renderHTML: ({ HTMLAttributes }) => ['h1', HTMLAttributes, 0],
})
const Doc = Node.create({ name: 'doc', topNode: true, content: 'title block*' })

// Keep this list in step with the server whitelist in pages/content.py.
const extensions = [
  Doc,
  Title,
  StarterKit.configure({
    document: false,
    heading: { levels: [2, 3] },
    code: false,
    codeBlock: false,
    horizontalRule: false,
    link: false,
  }),
  ...toneMarks,
  Placeholder.configure({
    showOnlyCurrent: false,
    placeholder: ({ node, hasAnchor }) => (node.type.name === 'title' ? 'Untitled' : hasAnchor ? 'Start writing…' : ''),
  }),
]

// Mount with a page that has finished loading (the editor reads its content only once).
export default function DocEditor({ page, canWrite, onSaved }) {
  const [dirty, setDirty] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(null)
  const savedJson = useRef('') // last saved document; "dirty" is measured against it

  const initial = docFor(page)
  const editor = useEditor({
    extensions,
    content: initial,
    editable: canWrite,
    autofocus: canWrite && !initial.content[0].content ? 'start' : false,
    onCreate: ({ editor }) => (savedJson.current = JSON.stringify(editor.getJSON())),
    // ponytail: stringify per keystroke is O(document size); debounce if big pages feel slow
    onUpdate: ({ editor }) => setDirty(JSON.stringify(editor.getJSON()) !== savedJson.current),
  })

  async function save() {
    const content = editor.getJSON()
    const sent = JSON.stringify(content)
    setPending(true)
    setError(null)
    try {
      const saved = await api(`/api/pages/${page.id}/`, { method: 'PATCH', body: { content } })
      savedJson.current = sent
      setDirty(JSON.stringify(editor.getJSON()) !== sent) // typing during the request keeps it dirty
      onSaved(saved)
    } catch (err) {
      const errors = fieldErrors(err)
      setError(errors.content ?? errors.form ?? 'Could not save the page.')
    }
    setPending(false)
  }

  return (
    <section className="doc">
      <div className="doc__bar">
        {canWrite && editor ? <EditorToolbar editor={editor} /> : null}
        <div className="doc__save">
          {canWrite ? (
            <>
              <p className="doc__note t-caption t-muted" role="status">
                {dirty ? '' : 'All changes saved'}
              </p>
              <Button size="sm" loading={pending} disabled={!dirty} onClick={save}>
                Save
              </Button>
            </>
          ) : (
            <Badge icon={Lock}>Read only</Badge>
          )}
        </div>
      </div>
      {error && <Alert>{error}</Alert>}
      <EditorContent editor={editor} className="doc__body" />
    </section>
  )
}
