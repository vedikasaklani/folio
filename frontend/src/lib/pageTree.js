// Lazily loaded page tree, normalized: `pages` maps id -> row, `levels` maps a parent id
// (or 'root') -> { ids, next } where `next` is the cursor URL of the next unloaded batch.
export const initialTree = { pages: {}, levels: {} }
export const keyOf = (parent) => parent ?? 'root'

// The server orders by id, so keeping ids ascending keeps rows in place across "load more" and local adds.
const sorted = (ids) => [...new Set(ids)].sort((a, b) => a - b)

function removeSubtree({ pages, levels }, id) {
  const doomed = []
  const walk = (i) => {
    doomed.push(i)
    ;(levels[i]?.ids ?? []).forEach(walk)
  }
  walk(id)

  const nextPages = { ...pages }
  const nextLevels = { ...levels }
  for (const i of doomed) {
    delete nextPages[i]
    delete nextLevels[i]
  }
  const key = keyOf(pages[id].parent)
  const siblings = levels[key].ids.filter((i) => i !== id)
  nextLevels[key] = { ...levels[key], ids: siblings }
  const parent = pages[id].parent
  if (parent != null) {
    nextPages[parent] = { ...pages[parent], has_children: siblings.length > 0 || levels[key].next !== null }
  }
  return { pages: nextPages, levels: nextLevels }
}

export function treeReducer(state, action) {
  switch (action.type) {
    case 'loaded': {
      const key = keyOf(action.parent)
      const pages = { ...state.pages }
      action.results.forEach((row) => (pages[row.id] = row))
      const ids = sorted([...(state.levels[key]?.ids ?? []), ...action.results.map((r) => r.id)])
      return { pages, levels: { ...state.levels, [key]: { ids, next: action.next } } }
    }
    case 'added': {
      const { page } = action
      const key = keyOf(page.parent)
      const pages = { ...state.pages, [page.id]: page }
      if (page.parent != null) pages[page.parent] = { ...pages[page.parent], has_children: true }
      const level = state.levels[key]
      // An unloaded level will include the new page when it first loads.
      const levels = level ? { ...state.levels, [key]: { ...level, ids: sorted([...level.ids, page.id]) } } : state.levels
      return { pages, levels }
    }
    case 'renamed':
      return { ...state, pages: { ...state.pages, [action.id]: { ...state.pages[action.id], name: action.name } } }
    case 'removed':
      return removeSubtree(state, action.id)
    default:
      return state
  }
}
