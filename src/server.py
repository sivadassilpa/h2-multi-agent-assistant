from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from .findProjects import handle_find_projects
from .multiAgentConnect import handle_query


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
async def root():
    return {
        "name": "H2 Multi-Agent Assistant",
        "status": "running",
        "docs": "/docs",
        "endpoints": ["/chat/conversations", "/chat/findProjects"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat/conversations")
async def chat_conversation(request: ChatRequest):
    reply = await handle_query(request.message)
    return {"reply": reply}


@app.post("/chat/findProjects")
async def find_projects(request: ChatRequest):
    reply = await handle_find_projects(request.message)
    return reply
