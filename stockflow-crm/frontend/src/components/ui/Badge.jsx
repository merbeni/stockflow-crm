const COLORS = {
  // order / invoice statuses
  pending:    'bg-yellow-100 text-yellow-800',
  processing: 'bg-primary text-primary-text',
  shipped:    'bg-secondary text-secondary-text',
  delivered:  'bg-green-100 text-green-800',
  confirmed:  'bg-green-100 text-green-800',
  rejected:   'bg-red-100 text-red-800',
  // stock movement types
  entry:      'bg-green-100 text-green-800',
  exit:       'bg-red-100 text-red-800',
  adjustment: 'bg-gray-100 text-gray-700',
  // confidence
  high:       'bg-conf-high-bg text-conf-high-text',
  medium:     'bg-conf-medium-bg text-conf-medium-text',
  low:        'bg-conf-low-bg text-conf-low-text',
}

const LABELS = { exit: 'sale' }

export default function Badge({ value }) {
  const cls = COLORS[value] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {LABELS[value] ?? value}
    </span>
  )
}
