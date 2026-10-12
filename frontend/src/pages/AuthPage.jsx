import { useState } from 'react'
import { api, setToken } from '../api'
import Alert from '../components/ui/Alert'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { Field, PasswordField } from '../components/ui/Field'
import { ArrowRight, FileText, History, Mail, User, Users } from '../components/ui/icons'
import Segmented from '../components/ui/Segmented'
import './AuthPage.css'

const MODES = [
  { value: 'login', label: 'Sign in' },
  { value: 'register', label: 'Create account' },
]

const COPY = {
  login: { title: 'Welcome back', lead: 'Sign in to pick up where you left off.', action: 'Sign in' },
  register: { title: 'Create your account', lead: 'Start your first workspace in a minute.', action: 'Create account' },
}

// Static showcase of what Folio does; also demos tinted cards, badges and icons.
const HIGHLIGHTS = [
  { tone: 'yellow', icon: FileText, title: 'Q4 roadmap', meta: 'Edited 2 min ago', badge: 'v12' },
  { tone: 'blue', icon: History, title: 'Restored v9', meta: 'Asha, yesterday' },
  { tone: 'pink', icon: Users, title: 'Design review notes', meta: '3 editors this week' },
]

// DRF returns { field: [messages] }; non_field_errors and network failures go to the form alert.
function toFormErrors(err) {
  if (!err.status) return { form: "Can't reach the server. Check that the API is running." }
  const errors = {}
  for (const [key, msgs] of Object.entries(err.data ?? {})) {
    errors[key === 'non_field_errors' ? 'form' : key] = [msgs].flat().join(' ')
  }
  if (errors.form?.startsWith('Unable to log in')) errors.form = 'Username or password is incorrect.'
  return Object.keys(errors).length ? errors : { form: 'Something went wrong. Try again.' }
}

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [values, setValues] = useState({ username: '', email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [pending, setPending] = useState(false)

  const isRegister = mode === 'register'
  const copy = COPY[mode]

  function handleChange(e) {
    const { name, value } = e.target
    setValues((v) => ({ ...v, [name]: value }))
  }

  function handleModeChange(next) {
    setMode(next)
    setErrors({})
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors({})
    setPending(true)
    try {
      const body = isRegister ? values : { username: values.username, password: values.password }
      const { token } = await api(`/api/auth/${isRegister ? 'register' : 'login'}/`, { method: 'POST', body })
      setToken(token)
      onAuth(token)
    } catch (err) {
      setErrors(toFormErrors(err))
      setPending(false)
    }
  }

  return (
    <main className="auth">
      <Card as="aside" variant="ink" className="auth__brand">
        <p className="auth__logo">folio</p>
        <div className="auth__pitch">
          <p className="t-display">Notes that remember every edit.</p>
          <p className="t-body auth__lead">Write with your team and restore any earlier version of a page.</p>
        </div>
        <ul className="auth__stack">
          {HIGHLIGHTS.map(({ tone, icon: Icon, title, meta, badge }) => (
            <li key={title}>
              <Card variant="tint" tone={tone} className="auth__item">
                <Icon aria-hidden="true" />
                <div>
                  <p className="t-heading">{title}</p>
                  <p className="t-caption">{meta}</p>
                </div>
                {badge && <Badge>{badge}</Badge>}
              </Card>
            </li>
          ))}
        </ul>
      </Card>

      <section className="auth__form">
        <Card className="auth__card">
          <Segmented label="Account" options={MODES} value={mode} onChange={handleModeChange} />
          <header className="auth__head">
            <h1 className="t-title">{copy.title}</h1>
            <p className="t-body t-muted">{copy.lead}</p>
          </header>

          <form className="auth__fields" onSubmit={handleSubmit}>
            {errors.form && <Alert>{errors.form}</Alert>}
            <Field
              label="Username"
              name="username"
              icon={User}
              autoComplete="username"
              value={values.username}
              onChange={handleChange}
              error={errors.username}
              required
            />
            {isRegister && (
              <Field
                label="Email"
                name="email"
                type="email"
                icon={Mail}
                autoComplete="email"
                value={values.email}
                onChange={handleChange}
                error={errors.email}
                required
              />
            )}
            <PasswordField
              label="Password"
              name="password"
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              value={values.password}
              onChange={handleChange}
              error={errors.password}
              hint={isRegister ? 'At least 8 characters, not a common password.' : undefined}
              required
            />
            <Button type="submit" block loading={pending} iconAfter={ArrowRight}>
              {copy.action}
            </Button>
          </form>
        </Card>
      </section>
    </main>
  )
}
