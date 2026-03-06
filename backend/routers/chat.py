from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from schemas.chat import ChatRequest, ChatResponse
from core.chatbot.intent import classify_intent
from core.chatbot.handlers import (
    handle_query, handle_absence, handle_explain, handle_smalltalk,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    college_id = current_user.college_id
    dept_id = current_user.dept_id or ""

    result = await classify_intent(body.message)
    intent = result.get("intent", "SMALLTALK")
    confidence = result.get("confidence", 0.0)
    entities = result.get("entities", {})

    if intent in ("QUERY", "GENERATE", "PUBLISH", "EXAM"):
        reply = await handle_query(body.message, entities, db, college_id, dept_id)
    elif intent in ("ABSENCE", "SUBSTITUTE"):
        reply = await handle_absence(body.message, entities, db, dept_id)
    elif intent == "EXPLAIN":
        reply = await handle_explain(body.message, entities, db, college_id, dept_id)
    else:
        reply = await handle_smalltalk(body.message)

    return ChatResponse(
        reply=reply,
        intent=intent,
        confidence=confidence,
    )
