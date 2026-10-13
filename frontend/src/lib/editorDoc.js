// The editor document is { doc: title, block* }. The server derives the page name and plain text from it.
const text = (s) => (s ? [{ type: 'text', text: s }] : undefined)

// Pages created before rich text have no `content`: show their name as the title and their old text as paragraphs.
// New pages are named "Untitled" by the client: show that as an empty title so the placeholder appears.
export function docFor({ name, content, text: legacyText }) {
  if (content?.type === 'doc') return content
  const body = (legacyText || '').split('\n').map((line) => ({ type: 'paragraph', content: text(line) }))
  return { type: 'doc', content: [{ type: 'title', content: text(name === 'Untitled' ? '' : name) }, ...body] }
}
