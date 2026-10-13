import { describe, expect, it } from 'vitest'
import { docFor } from './editorDoc'

describe('docFor', () => {
  it('passes a saved document through untouched', () => {
    const content = { type: 'doc', content: [{ type: 'title' }] }
    expect(docFor({ name: 'x', content, text: '' })).toBe(content)
  })

  it('builds title + paragraphs for legacy plain-text pages', () => {
    expect(docFor({ name: 'Old', content: {}, text: 'a\n\nb' }).content).toEqual([
      { type: 'title', content: [{ type: 'text', text: 'Old' }] },
      { type: 'paragraph', content: [{ type: 'text', text: 'a' }] },
      { type: 'paragraph', content: undefined },
      { type: 'paragraph', content: [{ type: 'text', text: 'b' }] },
    ])
  })

  it('shows a fresh "Untitled" page as an empty title', () => {
    expect(docFor({ name: 'Untitled', content: {}, text: '' }).content[0]).toEqual({ type: 'title', content: undefined })
  })
})
