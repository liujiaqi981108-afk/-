"""Base class for all 9 Studio Agents with telemetry and provider access."""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from app.config import ProviderSettings, get_settings
from app.models.schemas import AgentActivityEvent
from app.providers.base import (
    BaseImageProvider,
    BaseLLMProvider,
    BaseTTSProvider,
    BaseVideoProvider,
)
from app.providers.registry import (
    get_image_provider,
    get_llm_provider,
    get_tts_provider,
    get_video_provider,
)
from app.storage.project_store import ProjectStore, get_project_store


class BaseStudioAgent:
    """Shared foundation providing SSE logging, LLM/Image/Video/TTS providers, and store access."""

    agent_id: str = "agent_00"
    agent_name: str = "BaseAgent"

    def __init__(
        self,
        store: Optional[ProjectStore] = None,
        settings: Optional[ProviderSettings] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        image_provider: Optional[BaseImageProvider] = None,
        video_provider: Optional[BaseVideoProvider] = None,
        tts_provider: Optional[BaseTTSProvider] = None,
    ) -> None:
        self.store = store or get_project_store()
        self.settings = settings or get_settings()
        self._llm = llm_provider
        self._img = image_provider
        self._video = video_provider
        self._tts = tts_provider

    @property
    def llm(self) -> BaseLLMProvider:
        return self._llm or get_llm_provider(self.settings)

    @property
    def img(self) -> BaseImageProvider:
        return self._img or get_image_provider(self.settings)

    @property
    def video(self) -> BaseVideoProvider:
        return self._video or get_video_provider(self.settings)

    @property
    def tts(self) -> BaseTTSProvider:
        return self._tts or get_tts_provider(self.settings)

    async def emit(
        self,
        project_id: str,
        phase: str,
        message: str,
        level: Literal["info", "success", "warn", "prescription", "gate"] = "info",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        evt = AgentActivityEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            phase=phase,
            level=level,
            message=message,
            details=details or {},
        )
        await self.store.append_event(project_id, evt)
