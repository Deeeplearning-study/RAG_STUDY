import MessageList from './MessageList'

function ChatPanel({ messages, question, sending, onQuestionChange, onSubmit, endRef }) {
  return (
    <section className="chat-panel card">
      <div className="panel-head">
        <div>
          <h3>대화</h3>
          <p>검색된 문서 조각과 함께 답변이 내려옵니다.</p>
        </div>
      </div>

      <MessageList messages={messages} />
      <div ref={endRef} />

      <form className="composer" onSubmit={onSubmit}>
        <input
          type="text"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          placeholder="예: 이 문서에서 RAG는 어떻게 설명하고 있나요?"
        />
        <button type="submit" disabled={sending || !question.trim()}>
          {sending ? '전송 중...' : '질문 보내기'}
        </button>
      </form>
    </section>
  )
}

export default ChatPanel
