import { describe, expect, it } from 'vitest'
import { workspaceTone } from './tone'

const list = ['a', 'b', 'c', 'd', 'e'].map((name) => ({ name }))

describe('workspaceTone', () => {
  it('gives the first four workspaces four different colours', () => {
    expect(new Set(list.slice(0, 4).map((w) => workspaceTone(list, w))).size).toBe(4)
  })

  it('wraps around after the last colour', () => {
    expect(workspaceTone(list, list[4])).toBe(workspaceTone(list, list[0]))
  })

  it('depends on the position in the list, not on any display order', () => {
    const shuffledForDisplay = [list[3], list[0], list[1]]
    expect(shuffledForDisplay.map((w) => workspaceTone(list, w))).toEqual(['olive', 'yellow', 'blue'])
  })
})
