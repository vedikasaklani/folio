import { describe, expect, it } from 'vitest'
import { initialTree, treeReducer } from './pageTree'

const row = (id, parent = null, has_children = false) => ({ id, parent, name: `p${id}`, has_children })
const run = (...actions) => actions.reduce(treeReducer, initialTree)

describe('treeReducer', () => {
  it('appends batches without duplicates and keeps id order', () => {
    const s = run(
      { type: 'loaded', parent: null, results: [row(1), row(3)], next: 'url' },
      { type: 'added', page: row(9) },
      { type: 'loaded', parent: null, results: [row(3), row(5)], next: null },
    )
    expect(s.levels.root).toEqual({ ids: [1, 3, 5, 9], next: null })
  })

  it('adding a child marks the parent expandable and skips unloaded levels', () => {
    const s = run({ type: 'loaded', parent: null, results: [row(1)], next: null }, { type: 'added', page: row(2, 1) })
    expect(s.pages[1].has_children).toBe(true)
    expect(s.levels[1]).toBeUndefined() // will be fetched on expand, including page 2
  })

  it('removing a page drops its whole loaded subtree and fixes the parent flag', () => {
    const s = run(
      { type: 'loaded', parent: null, results: [row(1, null, true)], next: null },
      { type: 'loaded', parent: 1, results: [row(2, 1, true)], next: null },
      { type: 'loaded', parent: 2, results: [row(3, 2)], next: null },
      { type: 'removed', id: 2 },
    )
    expect(Object.keys(s.pages)).toEqual(['1'])
    expect(s.levels[1].ids).toEqual([])
    expect(s.levels[2]).toBeUndefined()
    expect(s.pages[1].has_children).toBe(false)
  })

  it('keeps has_children when unloaded siblings remain', () => {
    const s = run(
      { type: 'loaded', parent: null, results: [row(1, null, true)], next: null },
      { type: 'loaded', parent: 1, results: [row(2, 1)], next: 'more' },
      { type: 'removed', id: 2 },
    )
    expect(s.pages[1].has_children).toBe(true)
  })
})
