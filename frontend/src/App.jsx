import { useState } from 'react'
import { getToken, setToken } from './api'
import Button from './components/ui/Button'
import Card from './components/ui/Card'
import AuthPage from './pages/AuthPage'

function SignedIn({ onSignOut }) {
  return (
    <main style={{ display: 'grid', placeItems: 'center', minHeight: '100dvh', padding: 'var(--s-4)' }}>
      <Card style={{ display: 'grid', gap: 'var(--s-4)', maxWidth: '26rem' }}>
        <h1 className="t-title">You're signed in</h1>
        <p className="t-body t-muted">Workspaces and pages arrive in the next step.</p>
        <Button variant="soft" onClick={onSignOut}>
          Sign out
        </Button>
      </Card>
    </main>
  )
}

export default function App() {
  const [token, setSession] = useState(getToken)

  function signOut() {
    setToken(null)
    setSession(null)
  }

  return token ? <SignedIn onSignOut={signOut} /> : <AuthPage onAuth={setSession} />
}
