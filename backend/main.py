from fastapi import FastAPI

app = FastAPI(title="RAG Study Backend")


@app.get("/")
def read_root():
    return {"message": "RAG Study backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
