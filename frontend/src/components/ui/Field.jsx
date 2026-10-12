import { useId, useState } from 'react'
import { cx } from './cx'
import { Eye, EyeOff, Lock } from './icons'
import './Field.css'

// error: message shown under the field. invalid: red outline only (the message lives on another field).
export function Field({ label, error, invalid, hint, icon: Icon, trailing, className, ...inputProps }) {
  const id = useId()
  const message = error || hint
  const outlined = Boolean(error || invalid)
  return (
    <div className={cx('ui-field', className)}>
      <label htmlFor={id} className="t-label">
        {label}
      </label>
      <div className={cx('ui-field__control', outlined && 'is-invalid')}>
        {Icon && <Icon aria-hidden="true" />}
        <input
          id={id}
          aria-invalid={outlined || undefined}
          aria-describedby={message ? `${id}-msg` : undefined}
          {...inputProps}
        />
        {trailing}
      </div>
      {message && (
        <p id={`${id}-msg`} className={cx('ui-field__msg', error && 'ui-field__msg--error')} role={error ? 'alert' : undefined}>
          {message}
        </p>
      )}
    </div>
  )
}

export function PasswordField(props) {
  const [visible, setVisible] = useState(false)
  const Toggle = visible ? EyeOff : Eye
  return (
    <Field
      icon={Lock}
      {...props}
      type={visible ? 'text' : 'password'}
      trailing={
        <button
          type="button"
          className="ui-field__toggle"
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          onClick={() => setVisible((v) => !v)}
        >
          <Toggle aria-hidden="true" />
        </button>
      }
    />
  )
}
