import logging
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import ChatRequest, ChatResponse, DriveDiscoveryAgent
from .config import get_settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
conversation_store: dict[str, list[dict[str, str]]] = defaultdict(list)
agent_holder: dict[str, DriveDiscoveryAgent] = {}


def get_agent() -> DriveDiscoveryAgent:
    if "agent" not in agent_holder:
        agent_holder["agent"] = DriveDiscoveryAgent(settings=settings)
    return agent_holder["agent"]


app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    session_history = conversation_store[payload.session_id]
    session_history.append({"role": "user", "content": payload.message})

    try:
        agent = get_agent()
        response = await agent.chat(message=payload.message, history=session_history[:-1])
    except Exception as exc:
        logger.exception("Chat request failed")
        session_history.pop()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_history.append({"role": "assistant", "content": response.answer})
    conversation_store[payload.session_id] = session_history[-24:]
    return response


@app.delete("/chat/{session_id}")
async def clear_chat(session_id: str) -> dict[str, str]:
    conversation_store.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}
