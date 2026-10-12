import { cx } from './cx'
import './Badge.css'

// tone: neutral | pink | blue | yellow | olive
export default function Badge({ tone = 'neutral', icon: Icon, className, children }) {
  return (
    <span className={cx('ui-badge', `ui-badge--${tone}`, className)}>
      {Icon && <Icon aria-hidden="true" />}
      {children}
    </span>
  )
}
