import { useEditorState } from '@tiptap/react'
import { TONE_MARKS } from '../lib/palette'
import ToneMenu from './ToneMenu'
import {
  ALargeSmall,
  Baseline,
  Bold,
  Code,
  Heading2,
  Heading3,
  Highlighter,
  Italic,
  List,
  ListOrdered,
  Quote,
  SquareCode,
  Strikethrough,
  Underline,
} from './ui/icons'

const MENU_ICONS = { textColor: Baseline, highlight: Highlighter, fontSize: ALargeSmall }
const MENUS = Object.fromEntries(TONE_MARKS.map((m) => [m.mark, m]))

// Toolbar order. Plain entries toggle a format; { menu } opens a palette; { sep } is a divider.
// For a toggle: how to run it, and how to tell it is active at the cursor.
const ITEMS = [
  { label: 'Bold', icon: Bold, run: (c) => c.toggleBold(), active: (e) => e.isActive('bold') },
  { label: 'Italic', icon: Italic, run: (c) => c.toggleItalic(), active: (e) => e.isActive('italic') },
  { label: 'Underline', icon: Underline, run: (c) => c.toggleUnderline(), active: (e) => e.isActive('underline') },
  { label: 'Strikethrough', icon: Strikethrough, run: (c) => c.toggleStrike(), active: (e) => e.isActive('strike') },
  { label: 'Inline code', icon: Code, run: (c) => c.toggleCode(), active: (e) => e.isActive('code') },
  { sep: true },
  { menu: 'textColor' },
  { menu: 'highlight' },
  { menu: 'fontSize' },
  { sep: true },
  { label: 'Heading', icon: Heading2, run: (c) => c.toggleHeading({ level: 2 }), active: (e) => e.isActive('heading', { level: 2 }) },
  { label: 'Subheading', icon: Heading3, run: (c) => c.toggleHeading({ level: 3 }), active: (e) => e.isActive('heading', { level: 3 }) },
  { sep: true },
  { label: 'Bulleted list', icon: List, run: (c) => c.toggleBulletList(), active: (e) => e.isActive('bulletList') },
  { label: 'Numbered list', icon: ListOrdered, run: (c) => c.toggleOrderedList(), active: (e) => e.isActive('orderedList') },
  { label: 'Quote', icon: Quote, run: (c) => c.toggleBlockquote(), active: (e) => e.isActive('blockquote') },
  {
    label: 'Code block',
    hint: 'Code block (Tab indents; Esc then Tab picks the language; Tab again leaves)',
    icon: SquareCode,
    run: (c) => c.toggleCodeBlock(),
    active: (e) => e.isActive('codeBlock'),
  },
]

export default function EditorToolbar({ editor }) {
  // The editor does not re-render React on every transaction; this subscribes only to what the toolbar shows:
  // which toggles are active, and the current tone of each palette mark (null = none).
  const state = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      active: Object.fromEntries(ITEMS.filter((i) => i.label).map((i) => [i.label, i.active(e)])),
      tones: Object.fromEntries(TONE_MARKS.map((m) => [m.mark, e.getAttributes(m.mark).tone ?? null])),
    }),
  })

  return (
    <div className="toolbar" role="toolbar" aria-label="Formatting">
      {ITEMS.map((item, i) => {
        if (item.sep) return <span key={i} className="toolbar__sep" aria-hidden="true" />
        if (item.menu) {
          const { mark, ...menu } = MENUS[item.menu]
          return (
            <ToneMenu key={mark} editor={editor} mark={mark} icon={MENU_ICONS[mark]} current={state.tones[mark]} {...menu} />
          )
        }
        const { label, hint, icon: Icon, run } = item
        return (
          <button
            key={label}
            type="button"
            title={hint ?? label}
            aria-label={label}
            aria-pressed={state.active[label]}
            onMouseDown={(e) => e.preventDefault()} // keep focus and selection in the editor
            onClick={() => run(editor.chain().focus()).run()}
          >
            <Icon aria-hidden="true" />
          </button>
        )
      })}
    </div>
  )
}
