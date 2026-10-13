import { useCallback, useState } from 'react'
import { getToken, setToken } from './api'
import AuthPage from './pages/AuthPage'
import Home from './pages/Home'

export default function App() {
  const [token, setSession] = useState(getToken)

  const signOut = useCallback(() => {
    setToken(null)
    setSession(null)
  }, [])

  return token ? <Home onSignOut={signOut} /> : <AuthPage onAuth={setSession} />
}
