import StatusCards from './sidebar/StatusCards'
import UploadPanel from './sidebar/UploadPanel'
import DocumentList from './sidebar/DocumentList'

function Sidebar({ health, documents, uploading, onUploadChange, notice, onRefresh }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="badge">RAG_STUDY</span>
        <h1>PDF 기반 RAG</h1>
        <p>문서를 /pdf에 넣거나 직접 업로드해서 Chroma DB에 자동 반영하는 토이 프로젝트용 백엔드/프론트.</p>
      </div>

      <div className="card">
        <h2>상태</h2>
        <StatusCards health={health} documents={documents} />
        <p className="hint">폴더 감시가 켜져 있어서 /pdf에 넣은 파일도 자동으로 인덱싱됩니다.</p>
        <button className="ghost-btn" type="button" onClick={onRefresh} style={{ marginTop: '12px', width: '100%' }}>
          새로고침
        </button>
      </div>

      <UploadPanel uploading={uploading} onUploadChange={onUploadChange} notice={notice} />
      <DocumentList documents={documents} />
    </aside>
  )
}

export default Sidebar
