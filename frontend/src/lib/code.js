import { createLowlight } from 'lowlight'
import bash from 'highlight.js/lib/languages/bash'
import css from 'highlight.js/lib/languages/css'
import java from 'highlight.js/lib/languages/java'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import sql from 'highlight.js/lib/languages/sql'
import typescript from 'highlight.js/lib/languages/typescript'
import xml from 'highlight.js/lib/languages/xml'
import yaml from 'highlight.js/lib/languages/yaml'

// Only these languages are bundled; add one here (and an alias if editors name it differently) to support more.
export const lowlight = createLowlight()
lowlight.register({ bash, css, java, javascript, json, python, sql, typescript, xml, yaml })
lowlight.registerAlias({
  javascript: ['js', 'jsx', 'javascriptreact', 'mjs'],
  typescript: ['ts', 'tsx', 'typescriptreact'],
  python: ['py'],
  bash: ['sh', 'shell', 'shellscript', 'zsh'],
  xml: ['html', 'svg', 'vue-html'],
  yaml: ['yml'],
  json: ['jsonc'],
})

// The picker's choices (value = the stored name). Every name must be registered above (code.test.js checks it).
export const CODE_LANGUAGES = [
  { value: 'bash', label: 'Bash' },
  { value: 'css', label: 'CSS' },
  { value: 'html', label: 'HTML' },
  { value: 'java', label: 'Java' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'json', label: 'JSON' },
  { value: 'python', label: 'Python' },
  { value: 'sql', label: 'SQL' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'yaml', label: 'YAML' },
]

// Unknown or missing languages stay uncoloured: guessing would paint logs and plain text at random.
lowlight.highlightAuto = (value) => ({ type: 'root', children: [{ type: 'text', value }], data: { language: undefined, relevance: 0 } })
