# RAG_STUDY

토이프로젝트용 PDF RAG 구조입니다.

## 구성
- `frontend/`: React UI
- `backend/`: PDF 인덱싱 및 검색 API
- `pdf/`: 여기에 PDF를 넣으면 자동으로 인덱싱

## 백엔드 실행(의도)
```bash
cd backend
pip install -r requirements.txt
python main.py
```

## 프론트 실행(의도)
```bash
cd frontend
npm install
npm run dev
```

## 주요 동작
- `/pdf` 폴더의 PDF를 주기적으로 스캔해서 벡터 DB에 반영
- 프론트에서 PDF 업로드 가능
- `/api/chat`으로 질문하면 관련 문서 chunk를 검색해서 답변
- 나중에 `OLLAMA_MODEL` / `OLLAMA_BASE_URL` 설정으로 Ollama 연결 가능

## 환경 변수
- `RAG_EMBEDDING_MODEL`
- `RAG_TOP_K`
- `PDF_SCAN_INTERVAL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
