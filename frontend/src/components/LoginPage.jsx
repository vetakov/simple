import { useState } from 'react'
import { ArrowRight, LockKeyhole, Mail } from 'lucide-react'
import Brand from './Brand.jsx'

export default function LoginPage({ onLogin, error, isLoading }) {
  const [email, setEmail] = useState('demo@pulse.crm')
  const [password, setPassword] = useState('demo123')

  async function handleSubmit(event) {
    event.preventDefault()
    await onLogin({ email, password })
  }

  return (
    <main className="auth-layout">
      <div className="auth-visual" aria-hidden="true">
        <div className="visual-grid" />
        <div className="visual-orb orb-one" />
        <div className="visual-orb orb-two" />
        <div className="visual-copy">
          <Brand light />
          <p>Все отношения с клиентами<br />в одном рабочем пространстве.</p>
        </div>
      </div>
      <section className="auth-panel">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="mobile-brand"><Brand /></div>
          <p className="eyebrow">CRM для команды</p>
          <h1>С возвращением</h1>
          <p className="auth-subtitle">Войдите, чтобы продолжить работу</p>
          {error && <div className="form-error" role="alert">{error}</div>}
          <label htmlFor="email">Email</label>
          <div className="input-wrap">
            <Mail size={17} aria-hidden="true" />
            <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </div>
          <label htmlFor="password">Пароль</label>
          <div className="input-wrap">
            <LockKeyhole size={17} aria-hidden="true" />
            <input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </div>
          <button className="primary-button login-button" disabled={isLoading} type="submit">
            {isLoading ? 'Выполняем вход…' : 'Войти в систему'}
            {!isLoading && <ArrowRight size={17} aria-hidden="true" />}
          </button>
          <p className="demo-note">Демо: <b>demo@pulse.crm</b> / <b>demo123</b></p>
        </form>
        <p className="auth-footer">© {new Date().getFullYear()} Pulse CRM</p>
      </section>
    </main>
  )
}
