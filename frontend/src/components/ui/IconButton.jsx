import { cx } from './cx'
import './IconButton.css'

// Utility-weight control: an icon with no visible text, so `label` is its accessible name and tooltip.
// variant: ghost | raised (floats on an edge, e.g. the sidebar handles). size: sm | md.
export default function IconButton({ icon: Icon, label, variant = 'ghost', size = 'md', className, ...rest }) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      className={cx('ui-iconbtn', `ui-iconbtn--${variant}`, `ui-iconbtn--${size}`, className)}
      {...rest}
    >
      <Icon aria-hidden="true" />
    </button>
  )
}
