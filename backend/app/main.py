from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.services.ingestion import start_folder_watcher, sync_pdf_folder

app = FastAPI(title="RAG Study Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/")
def read_root():
    return {"message": "RAG Study backend is running"}


@app.on_event("startup")
def startup_event() -> None:
    start_folder_watcher()
