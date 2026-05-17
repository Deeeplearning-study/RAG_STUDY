import ReactMarkdown from 'react-markdown'

function MessageList({ messages }) {
  return (
    <div className="messages">
      {messages.map((message) => (
        <article key={message.id} className={`message ${message.role}`}>
          <div className="bubble">
            <div className="bubble-meta">
              <strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong>
              <span>{message.time}</span>
            </div>
            <div className="markdown-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>

          {message.sources?.length ? (
            <div className="source-row">
              {message.sources.map((source, index) => (
                <div key={source.id ?? `${message.id}-${index}`} className="source-pill">
                  <span className="source-index">[{index + 1}]</span>
                  <span>
                    {source.title}
                    {source.page ? ` · p.${source.page}` : ''}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  )
}

export default MessageList
