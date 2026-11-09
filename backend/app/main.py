
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.chat.chat import router as chat_router
app = FastAPI(
    title = "BASIC Websockets APP",
)

# adding middleware

origins = ["http://localhost:3000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health")
async def health():
    return {"status": "ok"}
app.include_router(chat_router, prefix="", tags=["chat"])  
