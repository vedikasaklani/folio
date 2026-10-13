import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { TONE_MARKS } from './palette'

// A name missing from the server whitelist = a 400 on save; missing from the CSS = invisible formatting.
const read = (rel) => readFileSync(new URL(rel, import.meta.url), 'utf8')
const server = read('../../../pages/content.py')
const css = read('../components/DocEditor.css')

describe('palette stays in step with the server and the CSS', () => {
  for (const { mark, attr, tones } of TONE_MARKS) {
    const names = tones.map((t) => t.tone)

    it(`${mark}: same tones as pages/content.py`, () => {
      const line = server.split('\n').find((l) => l.trim().startsWith(`'${mark}':`))
      expect(line, `no '${mark}' entry in TONES`).toBeTruthy()
      const serverNames = [...line.matchAll(/'([A-Za-z]+)'/g)].map((m) => m[1]).slice(1) // first match is the key
      expect(serverNames).toEqual(names)
    })

    it(`${mark}: every tone has a CSS rule`, () => {
      for (const name of names) expect(css).toContain(`[${attr}='${name}']`)
    })
  }
})
