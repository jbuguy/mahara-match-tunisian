import { useId, type FormEvent, type ReactNode } from 'react'

export type ChatMessage = { role: 'user' | 'assistant'; content: string }

type ChatPanelProps = {
  variant?: 'compact' | 'dedicated'
  title: string
  className?: string
  eyebrow?: string
  description?: string
  messages: ChatMessage[]
  value: string
  onValueChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  pending?: boolean
  error?: string
  placeholder?: string
  inputLabel: string
  emptyMessage: string
  submitLabel?: string
  pendingLabel?: string
  assistantName?: string
  userName?: string
  maxLength?: number
  composerDisabled?: boolean
  composerActions?: ReactNode
  statusNote?: ReactNode
  children?: ReactNode
}

export function ChatPanel({
  variant = 'dedicated',
  title,
  className,
  eyebrow,
  description,
  messages,
  value,
  onValueChange,
  onSubmit,
  pending = false,
  error,
  placeholder = 'Write a message…',
  inputLabel,
  emptyMessage,
  submitLabel = 'Send',
  pendingLabel = 'Sending…',
  assistantName = 'Mahara',
  userName = 'You',
  maxLength = 2000,
  composerDisabled = false,
  composerActions,
  statusNote,
  children,
}: ChatPanelProps) {
  const inputId = useId()
  return (
    <section className={`chat-panel chat-panel-${variant}${className ? ` ${className}` : ''}`} aria-label={title}>
      <header className="chat-panel-header">
        <div>
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          <h3>{title}</h3>
          {description && <p className="chat-panel-description">{description}</p>}
        </div>
        <span className="chat-avatar" aria-hidden="true">M</span>
      </header>
      <div className="chat-panel-messages" aria-live="polite" aria-relevant="additions text">
        {messages.length === 0 && <p className="chat-panel-empty">{emptyMessage}</p>}
        {messages.map((item, index) => <article className={`conversation-message ${item.role}`} key={`${index}-${item.role}`}>
          <span>{item.role === 'assistant' ? assistantName : userName}</span>
          <p>{item.content}</p>
        </article>)}
        {pending && <p className="chat-panel-pending" role="status">{pendingLabel}</p>}
      </div>
      {!composerDisabled && <form className="chat-panel-composer" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor={inputId}>{inputLabel}</label>
        <textarea
          id={inputId}
          rows={variant === 'compact' ? 2 : 3}
          maxLength={maxLength}
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          placeholder={placeholder}
          required
        />
        {statusNote}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="chat-panel-controls">
          {composerActions}
          <button className="primary-btn" type="submit" disabled={pending || !value.trim()}>
            {pending ? pendingLabel : submitLabel}
          </button>
        </div>
      </form>}
      {children}
    </section>
  )
}
