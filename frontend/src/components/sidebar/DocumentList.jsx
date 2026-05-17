function DocumentList({ documents, className = "card" }) {
  return (
    <div className={className}>
      <h2>문서 목록</h2>
      <div className="doc-list">
        {documents.length ? (
          documents.map((doc) => (
            <div key={doc.source_path} className="doc-item" title={doc.filename}>
              <strong>{doc.filename}</strong>
              <span>
                {doc.pages} pages · {doc.chunks} chunks
              </span>
            </div>
          ))
        ) : (
          <p className="hint">아직 인덱싱된 PDF가 없습니다.</p>
        )}
      </div>
    </div>
  )
}

export default DocumentList
