import { Mark } from '@tiptap/react'
import { TONE_MARKS } from './palette'

// One TipTap mark per entry in palette.js. Saved as { type, attrs: { tone } } and drawn as
// <span data-highlight="yellow">, which the CSS maps to design tokens. Pasted HTML only becomes
// a mark if it carries a known tone; foreign inline styles are dropped.
export const toneMarks = TONE_MARKS.map(({ mark, attr, tones }) => {
  const names = tones.map((t) => t.tone)
  return Mark.create({
    name: mark,
    addAttributes: () => ({
      tone: { default: null, parseHTML: (el) => el.getAttribute(attr), renderHTML: ({ tone }) => ({ [attr]: tone }) },
    }),
    parseHTML: () => [{ tag: `span[${attr}]`, getAttrs: (el) => (names.includes(el.getAttribute(attr)) ? null : false) }],
    renderHTML: ({ HTMLAttributes }) => ['span', HTMLAttributes, 0],
  })
})
