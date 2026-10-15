import { NodeViewContent, NodeViewWrapper } from '@tiptap/react'
import { CODE_LANGUAGES } from '../lib/code'

// How a code block is drawn in the editor: the block plus its language picker. The picker is real UI inside the
// document (contentEditable off), so the language is always one click away, even for a block created empty.
// null and "plaintext" both mean uncoloured; choosing Plain text stores "plaintext".
// The select is out of the tab order (tabIndex -1) so Tab never walks through every block's picker; keyboard users
// reach it with Esc then Tab (see lib/codeBlock.js) and one more Tab leaves the editor.
export default function CodeBlockView({ node, editor, updateAttributes }) {
  const language = node.attrs.language ?? 'plaintext'
  const listed = CODE_LANGUAGES.some((l) => l.value === language)
  return (
    <NodeViewWrapper className="code-block">
      <div className="code-block__lang" contentEditable={false}>
        {editor.isEditable ? (
          <select aria-label="Code language" tabIndex={-1} value={language} onChange={(e) => updateAttributes({ language: e.target.value })}>
            <option value="plaintext">Plain text</option>
            {CODE_LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
            {listed || language === 'plaintext' ? null : <option value={language}>{language}</option>}
          </select>
        ) : language !== 'plaintext' ? (
          <span>{CODE_LANGUAGES.find((l) => l.value === language)?.label ?? language}</span>
        ) : null}
      </div>
      <pre data-language={language} spellCheck={false}>
        {/* the node view injects white-space: pre-wrap inline, which would wrap long lines; keep the pre's `pre` */}
        <NodeViewContent as="code" style={{ whiteSpace: 'inherit' }} />
      </pre>
    </NodeViewWrapper>
  )
}
