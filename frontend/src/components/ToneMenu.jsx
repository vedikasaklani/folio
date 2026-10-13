import { useEffect, useId, useRef } from 'react'
import './ToneMenu.css'

const MENU_WIDTH = 192 // keep in step with .tone-menu width (12rem), used to keep the menu on screen

// Toolbar button + native popover listing a mark's tones. Each row previews the real rendering
// (the sample carries the same data attribute the document uses) and also shows a text name.
export default function ToneMenu({ editor, mark, attr, label, icon: Icon, tones, current }) {
  const id = useId()
  const button = useRef(null)
  const menu = useRef(null)

  useEffect(() => {
    const el = menu.current
    // The editor swallows Escape (default-prevented), so the browser never sends its own close request.
    const onKey = (e) => {
      if (e.key !== 'Escape') return
      e.stopPropagation()
      el.hidePopover()
    }
    const onBeforeToggle = (e) => {
      if (e.newState === 'open') {
        const r = button.current.getBoundingClientRect()
        el.style.top = `${r.bottom + 6}px`
        el.style.left = `${Math.max(8, Math.min(r.left, window.innerWidth - MENU_WIDTH - 8))}px`
        document.addEventListener('keydown', onKey, true)
      } else {
        document.removeEventListener('keydown', onKey, true)
      }
    }
    el.addEventListener('beforetoggle', onBeforeToggle)
    return () => {
      el.removeEventListener('beforetoggle', onBeforeToggle)
      document.removeEventListener('keydown', onKey, true)
    }
  }, [])

  function choose(tone) {
    const chain = editor.chain().focus()
    if (tone) chain.setMark(mark, { tone }).run()
    else chain.unsetMark(mark, { extendEmptyMarkRange: true }).run()
    menu.current.hidePopover()
  }

  const keepEditorFocus = (e) => e.preventDefault()
  return (
    <>
      <button
        ref={button}
        type="button"
        title={current ? `${label}: ${current}` : label}
        aria-label={label}
        aria-haspopup="true"
        aria-pressed={current !== null}
        popoverTarget={id}
        onMouseDown={keepEditorFocus}
      >
        <Icon aria-hidden="true" />
      </button>
      <div ref={menu} id={id} popover="auto" className="tone-menu" role="group" aria-label={label}>
        {[{ tone: null, label: 'Default' }, ...tones].map((t) => (
          <button
            key={t.tone ?? 'default'}
            type="button"
            aria-pressed={current === t.tone}
            onMouseDown={keepEditorFocus}
            onClick={() => choose(t.tone)}
          >
            <span className="tone-menu__sample" {...(t.tone ? { [attr]: t.tone } : {})}>
              Aa
            </span>
            {t.label}
          </button>
        ))}
      </div>
    </>
  )
}
