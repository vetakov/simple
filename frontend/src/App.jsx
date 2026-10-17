import { useEffect, useState } from 'react'
import DashboardPage from './pages/DashboardPage.jsx'
import LoginPage from './components/LoginPage.jsx'
import { ApiError, currentUser, dashboard, signIn, signOut } from './lib/api.js'

export default function App() {
  const [state, setState] = useState({ status: 'checking', user: null, data: null, error: '' })
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function restoreSession() {
      try {
        const user = await currentUser()
        if (cancelled) return
        const data = await dashboard().catch(() => null)
        if (!cancelled) setState({ status: 'authenticated', user, data, error: '' })
      } catch {
        if (!cancelled) setState({ status: 'anonymous', user: null, data: null, error: '' })
      }
    }
    restoreSession()
    return () => { cancelled = true }
  }, [])

  async function handleLogin(credentials) {
    setIsLoading(true)
    setState((current) => ({ ...current, error: '' }))
    try {
      const result = await signIn(credentials.email, credentials.password)
      const user = result.user || { name: 'Алексей Петров', role: 'Администратор' }
      const data = await dashboard().catch(() => null)
      setState({ status: 'authenticated', user, data, error: '' })
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Не удалось выполнить вход'
      setState((current) => ({ ...current, status: 'anonymous', error: message }))
    } finally {
      setIsLoading(false)
    }
  }

  async function handleLogout() {
    await signOut()
    setState({ status: 'anonymous', user: null, data: null, error: '' })
  }

  if (state.status === 'checking') return <div className="page-loader" role="status"><span className="loader" />Загрузка Pulse CRM…</div>
  if (state.status === 'authenticated') return <DashboardPage user={state.user} data={state.data} onLogout={handleLogout} />
  return <LoginPage onLogin={handleLogin} error={state.error} isLoading={isLoading} />
}
