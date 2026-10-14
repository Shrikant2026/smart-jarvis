# from fastapi import FastAPI
# from logger import log_conversation
# from memory import store_memory, get_memory
# import requests

# app = FastAPI()

# OLLAMA_URL = "http://192.168.29.11:11434/api/generate"

# @app.post("/chat")
# def chat(prompt: str):
    
#     # Get past memory
#     past_memory = get_memory(prompt)
    
#     context = ""
#     if past_memory:
#         context = "Previous memory:\n" + "\n".join(past_memory[0])
    
#     final_prompt = context + "\nUser: " + prompt

#     response = requests.post(OLLAMA_URL, json={
#         "model": "llama3",
#         "prompt": final_prompt,
#         "stream": False
#     })

#     output = response.json()["response"]

#     # Store new memory
#     store_memory(prompt + " " + output)
#     log_conversation(prompt, output)
#     return {"response": output}
   

# @app.post("/learn")
# def learn(text: str):
#     store_memory(text)
#     return {"message": "Learned successfully"}

from fastapi import FastAPI

from app.core.config import HOST, PORT
from app.routes import chat, learn

app = FastAPI(
    title="Smart Jarvis API",
    version="0.2.0",
    description="Personal AI assistant with local memory.",
)

app.include_router(chat.router)
app.include_router(learn.router)


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