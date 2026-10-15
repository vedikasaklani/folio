import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight'
import { mergeAttributes, ReactNodeViewRenderer } from '@tiptap/react'
import CodeBlockView from '../components/CodeBlockView'
import { lowlight } from './code'

// TipTap's code block already: turns a VS Code paste into a block with its language (plain text, so every space and
// line break survives), reads <pre><code class="language-x"> from web pages, and creates blocks from ```lang.
// On top of that: Tab indents inside a block (never a keyboard trap: Esc then Tab jumps to the block's language
// picker, and since the pickers are out of the normal tab order, one more Tab leaves the editor),
// and each block carries a language picker (CodeBlockView). Guessing the language from the text is not an option:
// highlight.js reads SQL as CSS and Java as TypeScript, so the language is chosen, pasted in, or typed after the fence.
export const CodeBlock = CodeBlockLowlight.extend({
  addStorage() {
    return { tabLeaves: false }
  },

  addKeyboardShortcuts() {
    const base = this.parent?.() ?? {}
    const inBlock = () => this.editor.isActive(this.name)
    const disarm = () => (this.storage.tabLeaves = false)
    return {
      ...base,
      Escape: () => (inBlock() ? (this.storage.tabLeaves = true) : false),
      // armed: hand focus to this block's picker (read-only editors have none: let the browser move on)
      Tab: (ctx) => {
        if (!this.storage.tabLeaves) return base.Tab(ctx)
        disarm()
        const wrapper = this.editor.view.nodeDOM(this.editor.state.selection.$from.before())
        const picker = wrapper?.querySelector?.('select')
        picker?.focus()
        return Boolean(picker)
      },
      // armed: the browser moves focus backwards out of the editor
      'Shift-Tab': (ctx) => (this.storage.tabLeaves ? (disarm(), false) : base['Shift-Tab'](ctx)),
    }
  },

  addNodeView() {
    return ReactNodeViewRenderer(CodeBlockView)
  },

  onSelectionUpdate() {
    this.storage.tabLeaves = false // any cursor move or keystroke cancels the Esc
  },

  renderHTML({ node, HTMLAttributes }) {
    const language = node.attrs.language
    return [
      'pre',
      mergeAttributes(this.options.HTMLAttributes, HTMLAttributes, { 'data-language': language || undefined, spellcheck: 'false' }),
      ['code', { class: language ? this.options.languageClassPrefix + language : null }, 0],
    ]
  },
}).configure({ lowlight, enableTabIndentation: true, tabSize: 2 })
