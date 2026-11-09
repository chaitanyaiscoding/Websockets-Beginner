
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.chat.chat import router as chat_router
from app.config import settings
app = FastAPI(
    title = "BASIC Websockets APP",
)

# adding middleware
# CORS covers normal HTTP requests (like /health). WebSockets skip CORS,
# so chat.py checks the same settings.allowed_origins list itself.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health")
async def health():
    return {"status": "ok"}
app.include_router(chat_router, prefix="", tags=["chat"])  
