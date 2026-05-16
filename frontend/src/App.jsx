import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const INITIAL_MESSAGES = [
  {
    id: 'welcome',
    role: 'assistant',
    content:
      'PDF를 /pdf 폴더에 넣거나, 아래 업로드 박스에서 바로 넣으면 자동으로 벡터DB에 들어갑니다. 질문을 보내면 관련 문서 조각을 찾아 답변해요.',
    sources: [],
    time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
  },
]

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options)
  const text = await response.text()
  if (!response.ok) {
    throw new Error(text || `HTTP ${response.status}`)
  }
  return text ? JSON.parse(text) : null
}

function formatTime(ts) {
  const date = ts ? new Date(ts * 1000) : new Date()
  return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}

function App() {
  const [health, setHealth] = useState(null)
  const [documents, setDocuments] = useState([])
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [question, setQuestion] = useState('')
  const [sending, setSending] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const endRef = useRef(null)
  const fileInputRef = useRef(null)

  const stats = useMemo(
    () => [
      { label: 'Indexed files', value: health?.indexed_files ?? documents.length ?? 0 },
      { label: 'Vector DB', value: health?.collection ?? 'Chroma' },
      { label: 'Embedding', value: health?.embedding_model ? 'Ready' : 'Loading' },
    ],
    [health, documents.length],
  )

  const refreshAll = async () => {
    try {
      const [healthData, docsData] = await Promise.all([requestJson('/api/health'), requestJson('/api/documents')])
      setHealth(healthData)
      setDocuments(docsData.documents ?? [])
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '서버에 연결할 수 없습니다.')
    }
  }

  useEffect(() => {
    refreshAll()
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  const handleUpload = async (event) => {
    const files = Array.from(event.target.files ?? [])
    if (!files.length) return

    const pdfFiles = files.filter((file) => file.name.toLowerCase().endsWith('.pdf'))
    if (!pdfFiles.length) {
      setNotice('PDF 파일만 업로드할 수 있어요.')
      return
    }

    const formData = new FormData()
    pdfFiles.forEach((file) => formData.append('files', file))

    setUploading(true)
    setNotice('업로드 중...')
    setError('')

    try {
      const response = await fetch(`${API_BASE}/api/documents/upload`, {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail || '업로드 실패')
      }
      setNotice(`업로드 완료: ${data.uploaded?.join(', ') || '파일 없음'}`)
      await refreshAll()
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setError(err instanceof Error ? err.message : '업로드 실패')
    } finally {
      setUploading(false)
    }
  }

  const sendQuestion = async (event) => {
    event.preventDefault()
    const prompt = question.trim()
    if (!prompt || sending) return

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: prompt,
      sources: [],
      time: formatTime(),
    }
    const pendingId = `pending-${Date.now()}`
    const pendingMessage = {
      id: pendingId,
      role: 'assistant',
      content: '관련 문서를 찾는 중...',
      sources: [],
      time: formatTime(),
      pending: true,
    }

    setMessages((current) => [...current, userMessage, pendingMessage])
    setQuestion('')
    setSending(true)
    setError('')

    try {
      const data = await requestJson('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt }),
      })

      const sources = (data.sources ?? []).map((source, index) => ({
        ...source,
        id: `${source.source_path}-${source.page ?? 'na'}-${source.chunk_index}-${index}`,
      }))

      setMessages((current) =>
        current
          .filter((message) => message.id !== pendingId)
          .concat({
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: data.answer,
            sources,
            time: formatTime(),
          }),
      )
      await refreshAll()
    } catch (err) {
      setMessages((current) => current.filter((message) => message.id !== pendingId))
      setError(err instanceof Error ? err.message : '질문 전송 실패')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="badge">RAG_STUDY</span>
          <h1>PDF 기반 RAG</h1>
          <p>문서를 /pdf에 넣거나 직접 업로드해서 Chroma DB에 자동 반영하는 토이 프로젝트용 백엔드/프론트.</p>
        </div>

        <div className="card">
          <h2>상태</h2>
          <div className="stats">
            {stats.map((item) => (
              <div key={item.label} className="stat">
                <span>{item.label}</span>
                <strong>{String(item.value)}</strong>
              </div>
            ))}
          </div>
          <p className="hint">폴더 감시가 켜져 있어서 /pdf에 넣은 파일도 자동으로 인덱싱됩니다.</p>
        </div>

        <div className="card">
          <h2>PDF 업로드</h2>
          <input ref={fileInputRef} className="file-input" type="file" accept="application/pdf" multiple onChange={handleUpload} />
          <button className="secondary-btn" type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? '업로드 중...' : 'PDF 선택'}
          </button>
          <p className="hint">업로드하면 파일이 자동으로 /pdf 폴더에 저장되고, 바로 벡터DB에 들어갑니다.</p>
          {notice ? <div className="notice success">{notice}</div> : null}
        </div>

        <div className="card">
          <h2>문서 목록</h2>
          <div className="doc-list">
            {documents.length ? (
              documents.map((doc) => (
                <div key={doc.source_path} className="doc-item">
                  <strong>{doc.filename}</strong>
                  <span>{doc.pages} pages · {doc.chunks} chunks</span>
                </div>
              ))
            ) : (
              <p className="hint">아직 인덱싱된 PDF가 없습니다.</p>
            )}
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">토이 프로젝트용 RAG 백엔드</p>
            <h2>질문 → 검색 → 답변</h2>
          </div>
          <button className="ghost-btn" type="button" onClick={refreshAll}>
            새로고침
          </button>
        </header>

        {error ? <div className="notice error">{error}</div> : null}

        <section className="content-grid">
          <section className="chat-panel card">
            <div className="panel-head">
              <div>
                <h3>대화</h3>
                <p>검색된 문서 조각과 함께 답변이 내려옵니다.</p>
              </div>
            </div>

            <div className="messages">
              {messages.map((message) => (
                <article key={message.id} className={`message ${message.role}`}>
                  <div className="bubble">
                    <div className="bubble-meta">
                      <strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong>
                      <span>{message.time}</span>
                    </div>
                    <p>{message.content}</p>
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
              <div ref={endRef} />
            </div>

            <form className="composer" onSubmit={sendQuestion}>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="예: 이 문서에서 RAG는 어떻게 설명하고 있나요?"
              />
              <button type="submit" disabled={sending || !question.trim()}>
                {sending ? '전송 중...' : '질문 보내기'}
              </button>
            </form>
          </section>

          <aside className="side-panel card">
            <h3>구현 범위 체크</h3>
            <ul className="checklist">
              <li>PDF 업로드 지원</li>
              <li>/pdf 폴더 자동 스캔</li>
              <li>Chroma DB 저장</li>
              <li>문서 출처 반환</li>
              <li>Ollama 연결 준비</li>
            </ul>
            <div className="divider" />
            <p className="hint">
              나중에 좋은 PC로 옮기면 <code>OLLAMA_MODEL</code>만 바꿔서 Gemma 계열 응답으로 붙일 수 있게 해뒀어요.
            </p>
          </aside>
        </section>
      </main>
    </div>
  )
}

export default App
