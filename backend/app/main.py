from fastapi import FastAPI

from app.core.config import HOST, PORT
from app.routes import chat, learn, content, comfyui, video_generation

app = FastAPI(
    title="Smart Jarvis API",
    version="0.2.0",
    description="Personal AI assistant with local memory.",
)

app.include_router(chat.router)
app.include_router(learn.router)
app.include_router(content.router)
app.include_router(comfyui.router)
app.include_router(video_generation.router)


@app.get("/")
def home():
    return {
        "message": "Jarvis running",
        "version": app.version,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
    )
