import { ArrowUpRight, Plus } from 'lucide-react'

const fallbackDeals = [
  { client: 'ООО «Север»', description: 'Обновление лицензий', amount: '₽ 420 000', stage: 'Переговоры', owner: 'Мария Волкова', tone: 'green' },
  { client: 'Ривер Банк', description: 'Корпоративный пакет', amount: '₽ 280 000', stage: 'Коммерческое', owner: 'Алексей Петров', tone: 'blue' },
  { client: 'Студия «Точка»', description: 'Поддержка продукта', amount: '₽ 95 000', stage: 'Закрытие', owner: 'Ирина Смирнова', tone: 'purple' },
]

export default function DealsTable({ deals = fallbackDeals, onCreate }) {
  const rows = deals.length ? deals : fallbackDeals
  return (
    <section className="deals-section">
      <div className="section-heading">
        <div><h2>Последние сделки</h2><p>Активность команды за текущий месяц</p></div>
        <button className="secondary-button" type="button" onClick={onCreate}><Plus size={17} /> Новая сделка</button>
      </div>
      <div className="table-scroll"><table className="deals-table">
        <thead><tr><th>Клиент</th><th>Сумма</th><th>Этап</th><th>Ответственный</th><th aria-label="Открыть" /></tr></thead>
        <tbody>{rows.map((deal, index) => <tr key={`${deal.client}-${index}`}>
          <td><strong>{deal.client}</strong><span>{deal.description}</span></td>
          <td className="deal-amount">{deal.amount}</td>
          <td><span className={`stage-pill ${deal.tone || 'green'}`}>{deal.stage}</span></td>
          <td className="deal-owner">{deal.owner}</td>
          <td><button className="row-action" aria-label={`Открыть сделку ${deal.client}`} type="button"><ArrowUpRight size={17} /></button></td>
        </tr>)}</tbody>
      </table></div>
    </section>
  )
}
