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
- GENERATE    : User wants to generate/create a NEW timetable from scratch
- PUBLISH     : User wants to publish/finalize a timetable
- EXPORT      : User wants to export/download a timetable as PDF or Excel
- QUERY       : User is asking a question about a timetable — free rooms, free slots,
                 faculty load, schedule details, availability, clashes, who teaches what,
                 what's scheduled when, etc.
- RESCHEDULE  : User wants to reschedule/move a lecture, add an extra lecture,
                 swap two slots, or modify an existing timetable entry
- ABSENCE     : User is reporting a faculty absence or wants a substitute
- SUBSTITUTE  : User wants to find/manage substitutes
- EXPLAIN     : User wants to understand a conflict or scheduling decision
- EXAM        : User wants to generate or view exam schedule
- SMALLTALK   : Greeting, thanks, off-topic, general chat

IMPORTANT classification rules:
- "free slot", "free room", "which room/class is free", "available rooms" → QUERY
- "reschedule", "move lecture", "swap", "add extra lecture", "change slot" → RESCHEDULE
- "generate", "create timetable", "build schedule" → GENERATE
- Entity extraction: always try to extract semester number (1-8), day name, and period number.
  For period, look for: "period 3", "P3", "3rd period", "slot 3", "2nd", etc.
  For day, look for: "Monday", "Mon", "tuesday", etc.

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
        result = await llm.json_chat(user_message, system=INTENT_SYSTEM)
        # Ensure entities exist
        result.setdefault("entities", {})
        return result
    except Exception:
        return _keyword_fallback(user_message)


def _keyword_fallback(msg: str) -> dict:
    m = msg.lower()
    import re

    # Extract entities
    entities: dict = {}
    # Semester
    sem_match = re.search(r'sem(?:ester)?\s*(\d)', m)
    if sem_match:
        entities["semester"] = int(sem_match.group(1))
    # Day
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday"):
        if day in m or day[:3] in m:
            entities["day"] = day.capitalize()
            break
    # Period
    period_match = re.search(r'(?:period|p|slot)\s*(\d)', m)
    if not period_match:
        period_match = re.search(r'(\d)(?:st|nd|rd|th)\s*(?:period|slot|lecture)', m)
    if period_match:
        entities["period"] = int(period_match.group(1))

    if any(w in m for w in ("generate", "create", "build")):
        return {"intent": "GENERATE", "confidence": 0.7, "entities": entities}
    if any(w in m for w in ("publish", "finalize", "release")):
        return {"intent": "PUBLISH", "confidence": 0.7, "entities": entities}
    if any(w in m for w in ("export", "download", "pdf", "excel", "print")):
        return {"intent": "EXPORT", "confidence": 0.7, "entities": entities}
    if any(w in m for w in ("reschedule", "move lecture", "swap", "extra lecture", "add lecture", "change slot")):
        return {"intent": "RESCHEDULE", "confidence": 0.7, "entities": entities}
    if any(w in m for w in ("absent", "absence", "not coming", "substitute", "sub")):
        return {"intent": "ABSENCE", "confidence": 0.7, "entities": entities}
    if any(w in m for w in ("free", "available", "clash", "conflict", "load", "utiliz",
                             "schedule", "who teach", "what class", "which room",
                             "which slot", "open slot")):
        return {"intent": "QUERY", "confidence": 0.6, "entities": entities}
    if any(w in m for w in ("exam", "test", "paper", "invigilat")):
        return {"intent": "EXAM", "confidence": 0.7, "entities": entities}
    if any(w in m for w in ("why", "explain", "because", "infeasible")):
        return {"intent": "EXPLAIN", "confidence": 0.7, "entities": entities}
    return {"intent": "SMALLTALK", "confidence": 0.5, "entities": entities}
