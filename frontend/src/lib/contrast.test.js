import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

// Highlight and text colour can be combined freely, so every pair has to be readable (WCAG AA = 4.5:1).
const tokens = readFileSync(new URL('../styles/tokens.css', import.meta.url), 'utf8')
const pick = (prefix) =>
  Object.fromEntries([...tokens.matchAll(new RegExp(`--${prefix}-([a-z]+): *(#[0-9a-f]{6})`, 'gi'))].map((m) => [m[1], m[2]]))

const channel = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
const luminance = (hex) => {
  const [r, g, b] = [1, 3, 5].map((i) => channel(parseInt(hex.slice(i, i + 2), 16) / 255))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
const contrast = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

const highlights = { ...pick('hl'), paper: '#fffbf0' } // paper = text colour on no highlight
const texts = { ...pick('text'), ink: '#121212' }

describe('rich-text colour tokens', () => {
  it('finds the tokens', () => {
    expect(Object.keys(pick('hl'))).toHaveLength(4)
    expect(Object.keys(pick('text'))).toHaveLength(4)
  })

  for (const [text, textHex] of Object.entries(texts)) {
    for (const [bg, bgHex] of Object.entries(highlights)) {
      it(`${text} text on ${bg} is at least 4.5:1`, () => {
        expect(contrast(textHex, bgHex)).toBeGreaterThanOrEqual(4.5)
      })
    }
  }
})
