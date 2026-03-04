"""
Chat API Route
==============

Handles incoming ad-hoc chat requests to the intelligence agent, classifying intent
using the RouterAgent and generating responses (with tool calls) via the IntelligenceAgent.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.router import RouterAgent
from agents.intelligence import IntelligenceAgent
from utils.llm_client import ResilientAsyncClient

logger = logging.getLogger(__name__)

router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = None
    domain: Optional[str] = "quantum"
    currentPage: Optional[str] = None
    sessionId: Optional[str] = "default"

class AgentResponseModel(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    tool_calls_made: int
    model: str
    route: Optional[str] = None
    frontend_command: Optional[Dict[str, Any]] = None


from fastapi.responses import StreamingResponse
from agents.session_store import get_session_store

@router.get("/stream")
async def chat_stream_endpoint(
    message: str,
    domain: Optional[str] = "quantum",
    currentPage: Optional[str] = None,
    sessionId: Optional[str] = "default"
):
    """
    Handle user chat message and stream the response using Server-Sent Events (SSE).
    """
    logger.info(f"[API] Chat stream request: session={sessionId} domain={domain}")
    
    async def event_generator():
        try:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                yield f'data: {{"error": "ANTHROPIC_API_KEY environment variable is missing"}}\n\n'
                return
                
            llm = ResilientAsyncClient(anthropic_api_key=api_key)
            active_domain = domain or "quantum"

            # 1. Route Intent
            router_agent = RouterAgent(llm_client=llm, domain=active_domain)
            route_result = await router_agent.route(message, domain=active_domain)

            # 2. Intelligence Agent
            intel_agent = IntelligenceAgent(llm_client=llm, domain=active_domain)
            
            # 3. Retrieve Session History
            session_store = get_session_store()
            actual_session_id = sessionId or "default"
            chat_session = await session_store.get_or_create(actual_session_id, "chat")
            
            # Format history for Claude
            conversation_history = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in chat_session.messages
            ]
            
            stream = intel_agent.answer_stream(
                user_message=message,
                conversation_history=conversation_history,
                route_hint=route_result.route,
                domain=active_domain,
                session_id=actual_session_id
            )
            
            final_content = ""
            final_sources = []
            
            async for chunk in stream:
                event = chunk.get("event", "message")
                data = chunk.get("data", {})
                
                # Capture text for history
                if event == "text_delta":
                    final_content += data.get("text", "")
                elif event == "complete":
                    final_sources = data.get("sources", [])
                
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
                
            # 4. Save to Session Store once complete
            chat_session.messages.append({"role": "user", "content": message})
            if final_content:
                chat_session.messages.append({
                    "role": "assistant", 
                    "content": final_content,
                    "sources": final_sources
                })
            await session_store.save(chat_session)
                
        except Exception as e:
            logger.error(f"[API] Chat stream error: {e}")
            yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("")
@router.post("/")
async def chat_endpoint(request: ChatRequest) -> AgentResponseModel:
    """
    Handle user chat message, route intent, and get agent response.
    """
    logger.info(f"[API] Chat request received: session={request.sessionId} domain={request.domain}")
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is missing")
            
        llm = ResilientAsyncClient(anthropic_api_key=api_key)
        domain = request.domain or "quantum"

        # 1. Route Intent
        router_agent = RouterAgent(llm_client=llm, domain=domain)
        route_result = await router_agent.route(request.message, domain=domain)

        # 2. Intelligence Agent
        intel_agent = IntelligenceAgent(llm_client=llm, domain=domain)
        
        # Convert Pydantic models to dicts for the agent
        history_dicts = []
        if request.history:
            history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]

        response = await intel_agent.answer(
            user_message=request.message,
            conversation_history=history_dicts,
            route_hint=route_result.route,
            domain=domain,
            session_id=request.sessionId or "default"
        )

        return AgentResponseModel(
            answer=response.answer,
            sources=response.sources,
            tool_calls_made=response.tool_calls_made,
            model=response.model,
            route=route_result.route,
            frontend_command=response.frontend_command
        )

    except Exception as e:
        logger.error(f"[API] Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

