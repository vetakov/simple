import { useState } from 'react'
import { Bell, Menu, Search } from 'lucide-react'
import DealsTable from '../components/DealsTable.jsx'
import KpiCard from '../components/KpiCard.jsx'
import Sidebar from '../components/Sidebar.jsx'

const fallback = {
  metrics: {
    revenue: { value: '₽ 1,28 млн', trend: '18,4% к прошлому месяцу' },
    clients: { value: '+48', trend: '12,5% к прошлому месяцу' },
    deals: { value: '126', note: 'на ₽ 3,6 млн' },
    tasks: { value: '17', note: '5 с высоким приоритетом' },
  },
  deals: [],
}

export default function DashboardPage({ user, data, onLogout }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const dashboard = { ...fallback, ...(data || {}), metrics: { ...fallback.metrics, ...(data?.metrics || {}) } }
  const firstName = (user?.name || 'Алексей').split(' ')[0]
  const date = new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())

  return (
    <div className="app-shell">
      <Sidebar user={user} isOpen={menuOpen} onClose={() => setMenuOpen(false)} onLogout={onLogout} />
      <main className="dashboard-main">
        <header className="dashboard-header">
          <button className="icon-button menu-toggle" aria-label="Открыть меню" onClick={() => setMenuOpen(true)}><Menu size={21} /></button>
          <div className="welcome-copy"><p className="eyebrow">{date}</p><h1>Добрый день, {firstName} <span aria-hidden="true">👋</span></h1></div>
          <div className="header-actions"><button className="icon-button" aria-label="Поиск"><Search size={19} /></button><button className="icon-button notification" aria-label="Уведомления"><Bell size={19} /><i /></button><div className="header-avatar">{getInitials(user?.name || 'Алексей Петров')}</div></div>
        </header>
        <div className="dashboard-content">
          <section className="kpi-grid" aria-label="Ключевые показатели">
            <KpiCard type="revenue" label="Выручка за месяц" value={dashboard.metrics.revenue.value} trend={`↗ ${dashboard.metrics.revenue.trend}`} />
            <KpiCard type="clients" label="Новые клиенты" value={dashboard.metrics.clients.value} trend={`↗ ${dashboard.metrics.clients.trend}`} />
            <KpiCard type="deals" label="Сделки в работе" value={dashboard.metrics.deals.value} note={dashboard.metrics.deals.note} />
            <KpiCard type="tasks" label="Задачи на сегодня" value={dashboard.metrics.tasks.value} note={dashboard.metrics.tasks.note} />
          </section>
          <DealsTable deals={dashboard.deals} />
        </div>
      </main>
    </div>
  )
}

function getInitials(name) {
  return name.split(' ').slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}
