from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uuid
import sys
import os

# Ensure the backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.auth_service import get_current_user, FRONTEND_BASE_URL
import services.chat_service as chat_service

app = FastAPI(
    title="GemmaWatch Chat API",
    description="Dedicated AI chat service to avoid event loop blocking from background monitoring",
    version="2.0",
)

# CORS — allow credentials for cookie-based auth
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_BASE_URL, "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("INFO: Dedicated Chat Microservice started on port 8003.")

@app.post("/chat", tags=["chat"])
async def chat_query(body: dict, user: dict = Depends(get_current_user)):
    query = body.get("query", "").strip()
    session_id = body.get("session_id", str(uuid.uuid4()))
    result = await chat_service.chat(query, session_id, user.get("sub"))
    return {**result, "session_id": session_id}

@app.post("/chat/stream", tags=["chat"])
async def chat_stream_query(body: dict, user: dict = Depends(get_current_user)):
    """Streaming chat endpoint for lower perceived latency."""
    query = body.get("query", "").strip()
    session_id = body.get("session_id", str(uuid.uuid4()))
    
    async def event_generator():
        try:
            async for chunk in chat_service.chat_stream(query, session_id, user.get("sub")):
                yield chunk
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.get("/chat/history/{session_id}", tags=["chat"])
async def get_chat_history(session_id: str, user: dict = Depends(get_current_user)):
    return {"messages": chat_service.get_chat_history(session_id)}
