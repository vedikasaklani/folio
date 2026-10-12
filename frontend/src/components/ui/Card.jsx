import { cx } from './cx'
import './Card.css'

// variant: surface (sand) | tint (pass tone: pink | blue | yellow | olive) | ink (black)
export default function Card({ as: Tag = 'div', variant = 'surface', tone, className, ...rest }) {
  return <Tag className={cx('ui-card', `ui-card--${variant}`, tone && `ui-card--${tone}`, className)} {...rest} />
}
