export default function Brand({ light = false }) {
  return <div className={`brand ${light ? 'brand-light' : ''}`} aria-label="Pulse CRM">pulse<span>.</span></div>
}
