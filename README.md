# RAG_STUDY

## 구성
- `frontend/`: React UI
- `backend/`: PDF 인덱싱 및 검색 API
- `pdf/`: 여기에 PDF를 넣으면 자동으로 인덱싱

## 현재 구조
- 프론트는 `src/components/` 아래로 컴포넌트 분리
- 백엔드는 `backend/app/routers/`, `backend/app/services/`, `backend/app/core/`로 분리
- `backend/main.py`는 실행 진입점만 담당

## 주요 API
- `POST /api/documents/upload`: 프론트에서 PDF 업로드
- `POST /api/scan`: `/pdf` 폴더 강제 재스캔
- `GET /api/documents`: 인덱싱된 문서 목록
- `POST /api/chat`: 질문 → 검색 → 답변
- `GET /api/health`: 상태 확인

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
