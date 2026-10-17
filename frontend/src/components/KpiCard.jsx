import { ArrowUpRight, BriefcaseBusiness, CheckSquare, CircleDollarSign, UserPlus } from 'lucide-react'

const icons = { revenue: CircleDollarSign, clients: UserPlus, deals: BriefcaseBusiness, tasks: CheckSquare }

export default function KpiCard({ type, label, value, trend, note }) {
  const Icon = icons[type] || CircleDollarSign
  return (
    <article className="kpi-card">
      <div className="kpi-heading"><span>{label}</span><span className={`kpi-icon kpi-${type}`}><Icon size={17} /></span></div>
      <div className="kpi-value">{value}</div>
      {trend ? <div className="kpi-trend"><ArrowUpRight size={15} />{trend}</div> : <div className="kpi-note">{note}</div>}
    </article>
  )
}
