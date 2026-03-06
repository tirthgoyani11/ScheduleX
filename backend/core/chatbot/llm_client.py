# core/chatbot/llm_client.py
"""
Unified LLM client – Kimi K2.5 (NVIDIA NIM) primary, local Ollama fallback.
"""
from __future__ import annotations

import json
import logging
from openai import AsyncOpenAI
from config import settings

log = logging.getLogger(__name__)

# NVIDIA NIM config – override via .env
NVIDIA_API_KEY: str = settings.NVIDIA_API_KEY
NVIDIA_BASE_URL: str = settings.NVIDIA_BASE_URL
NVIDIA_MODEL: str = settings.NVIDIA_MODEL


class ChatLLM:
    """
    Provides .chat() (plain text) and .json_chat() (parsed dict) helpers.
    Uses NVIDIA NIM (Kimi K2.5) when an API key is configured,
    otherwise falls back to the local Ollama instance already in config.
    """

    def __init__(self) -> None:
        self.request_count = 0
        self.fallback_count = 0

        if NVIDIA_API_KEY and NVIDIA_API_KEY != "nvapi-xxxxxxxxxxxxxxxxxxxx":
            self._nvidia = AsyncOpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
        else:
            self._nvidia = None

        # Ollama exposes an OpenAI-compatible API on /v1
        self._ollama = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",  # Ollama ignores the key
        )

    # ── public helpers ────────────────────────────────────────
    async def chat(self, user_msg: str, *, system: str = "", thinking: bool = False) -> str:
        """Return a plain-text response."""
        return await self._call(user_msg, system=system, thinking=thinking)

    async def json_chat(self, user_msg: str, *, system: str = "") -> dict:
        """Return a parsed JSON dict from the LLM response."""
        raw = await self._call(user_msg, system=system or self._json_system(), thinking=False)
        return self._parse_json(raw)

    def status(self) -> dict:
        return {
            "kimi_requests_used": self.request_count,
            "kimi_requests_left": max(0, 1000 - self.request_count),
            "fallback_activations": self.fallback_count,
            "backend": "nvidia" if self._nvidia else "ollama",
        }

    # ── internals ─────────────────────────────────────────────
    async def _call(self, user_msg: str, *, system: str, thinking: bool) -> str:
        messages = [
            {"role": "system", "content": system or self._default_system()},
            {"role": "user", "content": user_msg},
        ]

        # Try NVIDIA NIM first
        if self._nvidia:
            try:
                kwargs: dict = dict(
                    model=NVIDIA_MODEL,
                    messages=messages,
                    temperature=0.7 if not thinking else 0.4,
                    max_tokens=1024,
                )
                resp = await self._nvidia.chat.completions.create(**kwargs)
                self.request_count += 1
                return resp.choices[0].message.content.strip()
            except Exception as exc:
                log.warning("Kimi K2.5 call failed (%s), falling back to Ollama", exc)
                self.fallback_count += 1

        # Ollama fallback
        try:
            resp = await self._ollama.chat.completions.create(
                model=settings.PRIMARY_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            log.error("Ollama fallback also failed: %s", exc)
            return f"LLM unavailable: {exc}"

    @staticmethod
    def _parse_json(raw: str) -> dict:
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start == -1:
            return {"error": "No JSON object in LLM response", "raw": raw[:300]}
        return json.loads(clean[start:end])

    @staticmethod
    def _default_system() -> str:
        return (
            "You are TimetableAI, an intelligent scheduling assistant for a university. "
            "You help admins and faculty manage timetables, find substitutes, and answer "
            "scheduling questions. Be concise, helpful, and friendly."
        )

    @staticmethod
    def _json_system() -> str:
        return (
            "You are a structured data extraction assistant. "
            'Return ONLY valid JSON. No explanation, no markdown, no extra text. '
            'If you cannot extract the requested structure, return {"error": "reason"}.'
        )


# Module-level singleton
llm = ChatLLM()
