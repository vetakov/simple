import { BriefcaseBusiness, CheckSquare, LayoutDashboard, LogOut, Settings, Users, X } from 'lucide-react'
import Brand from './Brand.jsx'

const navigation = [
  { label: 'Обзор', icon: LayoutDashboard, active: true },
  { label: 'Клиенты', icon: Users },
  { label: 'Сделки', icon: BriefcaseBusiness },
  { label: 'Задачи', icon: CheckSquare },
  { label: 'Настройки', icon: Settings },
]

export default function Sidebar({ user, isOpen, onClose, onLogout }) {
  return (
    <>
      {isOpen && <button className="sidebar-backdrop" aria-label="Закрыть меню" onClick={onClose} />}
      <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-top">
          <Brand light />
          <button className="icon-button close-menu" aria-label="Закрыть меню" onClick={onClose}><X size={19} /></button>
        </div>
        <nav className="main-nav" aria-label="Основная навигация">
          {navigation.map(({ label, icon: Icon, active }) => (
            <a className={active ? 'nav-link active' : 'nav-link'} href={`#${label.toLowerCase()}`} key={label} onClick={onClose}>
              <Icon size={19} strokeWidth={active ? 2.4 : 2} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <div className="sidebar-user">
          <div className="avatar">{getInitials(user?.name || 'Алексей Петров')}</div>
          <div className="sidebar-user-copy">
            <strong>{user?.name || 'Алексей Петров'}</strong>
            <span>{user?.role || 'Администратор'}</span>
          </div>
          <button className="icon-button sidebar-logout" aria-label="Выйти" onClick={onLogout}><LogOut size={17} /></button>
        </div>
      </aside>
    </>
  )
}

function getInitials(name) {
  return name.split(' ').slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}
