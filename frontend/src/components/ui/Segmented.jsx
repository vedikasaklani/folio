import { cx } from './cx'
import './Segmented.css'

export default function Segmented({ label, options, value, onChange }) {
  return (
    <div className="ui-seg" role="group" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          className={cx('ui-seg__item', o.value === value && 'is-active')}
          aria-pressed={o.value === value}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
