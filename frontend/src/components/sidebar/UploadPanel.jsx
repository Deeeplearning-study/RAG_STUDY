import { useRef } from 'react'

function UploadPanel({ uploading, onUploadChange, notice }) {
  const fileInputRef = useRef(null)

  return (
    <div className="card">
      <h2>PDF 업로드</h2>
      <input ref={fileInputRef} className="file-input" type="file" accept="application/pdf" multiple onChange={onUploadChange} />
      <button className="secondary-btn" type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
        {uploading ? '업로드 중...' : 'PDF 선택'}
      </button>
      <p className="hint">업로드하면 파일이 자동으로 /pdf 폴더에 저장되고, 바로 벡터DB에 들어갑니다.</p>
      {notice ? <div className="notice success">{notice}</div> : null}
    </div>
  )
}

export default UploadPanel
