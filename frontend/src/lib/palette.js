// The one list of text formats. Documents store only the `tone` name (e.g. "yellow"), never a colour or size.
// Three places must agree: this file, TONES in pages/content.py (the server whitelist) and the CSS rules in
// components/DocEditor.css. palette.test.js fails if they drift.
export const TONE_MARKS = [
  {
    mark: 'textColor',
    attr: 'data-text-color',
    label: 'Text colour',
    tones: [
      { tone: 'red', label: 'Red' },
      { tone: 'blue', label: 'Blue' },
      { tone: 'olive', label: 'Olive' },
      { tone: 'plum', label: 'Plum' },
    ],
  },
  {
    mark: 'highlight',
    attr: 'data-highlight',
    label: 'Highlight',
    tones: [
      { tone: 'yellow', label: 'Yellow' },
      { tone: 'pink', label: 'Pink' },
      { tone: 'blue', label: 'Blue' },
      { tone: 'olive', label: 'Olive' },
    ],
  },
  {
    mark: 'fontSize',
    attr: 'data-font-size',
    label: 'Text size',
    tones: [
      { tone: 'small', label: 'Small' },
      { tone: 'large', label: 'Large' },
      { tone: 'huge', label: 'Huge' },
    ],
  },
]
