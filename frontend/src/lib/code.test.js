import { describe, expect, it } from 'vitest'
import { CODE_LANGUAGES, lowlight } from './code'

const classes = (node) => [...(node.properties?.className ?? []), ...(node.children ?? []).flatMap(classes)]
const text = (node) => (node.type === 'text' ? node.value : (node.children ?? []).map(text).join(''))

describe('syntax highlighting setup', () => {
  const code = 'def f(x):\n\treturn "a"  # note\n'

  it('colours a known language and never changes the characters', () => {
    const tree = lowlight.highlight('python', code)
    expect(classes(tree)).toEqual(expect.arrayContaining(['hljs-keyword', 'hljs-string', 'hljs-comment']))
    expect(text(tree)).toBe(code) // tabs, trailing spaces and newlines survive highlighting
  })

  it('knows the language names editors send', () => {
    for (const name of ['js', 'jsx', 'javascriptreact', 'ts', 'tsx', 'typescriptreact', 'py', 'sh', 'shellscript', 'html', 'yml', 'jsonc']) {
      expect(lowlight.registered(name), name).toBe(true)
    }
  })

  it('has a grammar for every language the picker offers', () => {
    for (const { value } of CODE_LANGUAGES) expect(lowlight.registered(value), value).toBe(true)
  })

  it('leaves unknown languages uncoloured instead of guessing', () => {
    const source = 'SELECT 1; def f(): return "x"\n  indented'
    const tree = lowlight.highlightAuto(source)
    expect(classes(tree)).toEqual([])
    expect(text(tree)).toBe(source)
  })
})
