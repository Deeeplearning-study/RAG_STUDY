import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/chat/ChatPanel'
import { API_BASE, requestJson } from './lib/api'
import './App.css'

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
      <Sidebar
        health={health}
        documents={documents}
        uploading={uploading}
        onUploadChange={handleUpload}
        notice={notice}
        onRefresh={refreshAll}
      />

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
          <ChatPanel
            messages={messages}
            question={question}
            sending={sending}
            onQuestionChange={setQuestion}
            onSubmit={sendQuestion}
            endRef={endRef}
          />

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
