import { cx } from './cx'
import { LoaderCircle } from './icons'
import './Button.css'

export default function Button({
  variant = 'primary', // primary | soft | ghost
  size = 'md', // md | sm
  icon: Icon,
  iconAfter: IconAfter,
  loading = false,
  block = false,
  disabled,
  type = 'button',
  className,
  children,
  ...rest
}) {
  return (
    <button
      type={type}
      className={cx('ui-btn', `ui-btn--${variant}`, `ui-btn--${size}`, block && 'ui-btn--block', className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? (
        <span className="ui-btn__spin" aria-hidden="true">
          <LoaderCircle />
        </span>
      ) : (
        Icon && <Icon aria-hidden="true" />
      )}
      <span>{children}</span>
      {IconAfter && !loading && <IconAfter aria-hidden="true" />}
    </button>
  )
}
