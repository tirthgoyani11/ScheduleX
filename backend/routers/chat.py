from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from schemas.chat import ChatRequest, ChatResponse
from core.chatbot.intent import classify_intent
from core.chatbot.handlers import (
    handle_query, handle_absence, handle_explain, handle_smalltalk,
    handle_generate, handle_generate_all, handle_publish, handle_export,
    handle_reschedule,
)
from core.chatbot.generation_advisor import (
    pre_generation_analysis, post_generation_analysis, ai_suggest_assignments,
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

    if intent == "GENERATE_ALL":
        gen_result = await handle_generate_all(body.message, entities, db, college_id, dept_id)
        return ChatResponse(
            reply=gen_result["reply"],
            intent=intent,
            confidence=confidence,
            data=gen_result.get("data"),
        )
    elif intent == "GENERATE":
        gen_result = await handle_generate(body.message, entities, db, college_id, dept_id)
        return ChatResponse(
            reply=gen_result["reply"],
            intent=intent,
            confidence=confidence,
            data=gen_result.get("data"),
        )
    elif intent == "PUBLISH":
        pub_result = await handle_publish(body.message, entities, db, dept_id)
        return ChatResponse(
            reply=pub_result["reply"],
            intent=intent,
            confidence=confidence,
            data=pub_result.get("data"),
        )
    elif intent == "EXPORT":
        exp_result = await handle_export(body.message, entities, db, college_id, dept_id)
        return ChatResponse(
            reply=exp_result["reply"],
            intent=intent,
            confidence=confidence,
            data=exp_result.get("data"),
        )
    elif intent == "RESCHEDULE":
        res_result = await handle_reschedule(body.message, entities, db, college_id, dept_id)
        return ChatResponse(
            reply=res_result["reply"],
            intent=intent,
            confidence=confidence,
            data=res_result.get("data"),
        )
    elif intent in ("QUERY", "EXAM"):
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


@router.post("/analyze-before-generate")
async def analyze_before_generate(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """AI pre-generation analysis endpoint for the Generate page."""
    semester = body.get("semester", 1)
    faculty_subject_map = body.get("faculty_subject_map", {})
    return await pre_generation_analysis(
        semester, faculty_subject_map, db,
        current_user.dept_id or "", current_user.college_id,
    )


@router.post("/analyze-after-generate")
async def analyze_after_generate(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """AI post-generation analysis endpoint."""
    timetable_id = body.get("timetable_id", "")
    if not timetable_id:
        return {"error": "timetable_id is required"}
    return await post_generation_analysis(timetable_id, db)


@router.post("/suggest-assignments")
async def suggest_assignments(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """AI-powered faculty-subject assignment suggestions."""
    semester = body.get("semester", 1)
    return await ai_suggest_assignments(
        semester, db, current_user.dept_id or "",
    )
