# core/chatbot/intent.py
"""
Intent classification – uses the LLM with a keyword fallback.
"""
from __future__ import annotations

from .llm_client import llm

INTENT_SYSTEM = """
You are an intent classifier for a university timetable chatbot.
Classify the user message into EXACTLY ONE of these intents:

INTENTS:
- GENERATE   : User wants to generate/create a timetable
- PUBLISH    : User wants to publish/finalize a timetable
- QUERY      : User is asking a question about the timetable (rooms, faculty, schedule)
- ABSENCE    : User is reporting a faculty absence or wants a substitute
- SUBSTITUTE : User wants to find/manage substitutes
- EXPLAIN    : User wants to understand a conflict or scheduling decision
- EXAM       : User wants to generate or view exam schedule
- SMALLTALK  : Greeting, thanks, off-topic, general chat

Return ONLY this JSON, nothing else:
{
  "intent": "INTENT_NAME",
  "confidence": 0.0-1.0,
  "entities": {
    "faculty_name": null,
    "subject_name": null,
    "semester": null,
    "day": null,
    "period": null,
    "room_name": null
  }
}
"""


async def classify_intent(user_message: str) -> dict:
    try:
        return await llm.json_chat(user_message, system=INTENT_SYSTEM)
    except Exception:
        return _keyword_fallback(user_message)


def _keyword_fallback(msg: str) -> dict:
    m = msg.lower()
    if any(w in m for w in ("generate", "create", "build", "make")):
        return {"intent": "GENERATE", "confidence": 0.7, "entities": {}}
    if any(w in m for w in ("publish", "finalize", "release")):
        return {"intent": "PUBLISH", "confidence": 0.7, "entities": {}}
    if any(w in m for w in ("absent", "absence", "not coming", "substitute", "sub")):
        return {"intent": "ABSENCE", "confidence": 0.7, "entities": {}}
    if any(w in m for w in ("free", "available", "clash", "conflict", "load", "utiliz")):
        return {"intent": "QUERY", "confidence": 0.6, "entities": {}}
    if any(w in m for w in ("exam", "test", "paper", "invigilat")):
        return {"intent": "EXAM", "confidence": 0.7, "entities": {}}
    if any(w in m for w in ("why", "explain", "because", "infeasible")):
        return {"intent": "EXPLAIN", "confidence": 0.7, "entities": {}}
    return {"intent": "SMALLTALK", "confidence": 0.5, "entities": {}}
