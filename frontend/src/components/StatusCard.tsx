type StatusCardProps = {
  title: string
  description: string
  eyebrow?: string
  tone?: 'default' | 'success' | 'warning' | 'danger'
}

export function StatusCard({ title, description, eyebrow, tone = 'default' }: StatusCardProps) {
  return (
    <article className={`status-card tone-${tone}`}>
      {eyebrow ? <span className="status-card-eyebrow">{eyebrow}</span> : null}
      <h2>{title}</h2>
      <p>{description}</p>
    </article>
  )
}
