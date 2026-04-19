export default function Modal({ title, onClose, children, disabled = false }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-surface rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col border border-brand-border">
        <div className="flex items-center justify-between px-6 py-4 border-b border-brand-border">
          <h2 className="text-base font-semibold text-tx-primary">{title}</h2>
          <button onClick={onClose} disabled={disabled} className="text-tx-muted hover:text-tx-secondary text-xl leading-none disabled:opacity-30 disabled:cursor-not-allowed">&times;</button>
        </div>
        <div className="overflow-y-auto px-6 py-4 flex-1">{children}</div>
      </div>
    </div>
  )
}
