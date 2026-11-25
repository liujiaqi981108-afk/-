"""Runtime configuration and pluggable AI provider credentials manager."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = Path(os.getenv("STUDIO_WORKSPACES_DIR", str(BASE_DIR / "workspaces")))
STATIC_DIR = BASE_DIR / "static"

ProviderVendor = Literal[
    "mock",
    "flow_browser",
    "edge_tts",
    "openai",
    "gemini",
    "volcengine",
    "dashscope",
    "kling",
]


class ProviderSettings(BaseModel):
    """Pluggable provider configuration manageable via env vars or Web UI."""

    llm_vendor: ProviderVendor = Field(
        default_factory=lambda: os.getenv("STUDIO_LLM_VENDOR", "mock")  # type: ignore[return-value]
    )
    image_vendor: ProviderVendor = Field(
        default_factory=lambda: os.getenv("STUDIO_IMAGE_VENDOR", "mock")  # type: ignore[return-value]
    )
    video_vendor: ProviderVendor = Field(
        default_factory=lambda: os.getenv("STUDIO_VIDEO_VENDOR", "mock")  # type: ignore[return-value]
    )
    tts_vendor: ProviderVendor = Field(
        default_factory=lambda: os.getenv("STUDIO_TTS_VENDOR", "edge_tts")  # type: ignore[return-value]
    )

    # Local Chrome CDP -> Google Flow Web Automation (Zero API Key)
    flow_cdp_url: str = Field(
        default_factory=lambda: os.getenv("FLOW_CDP_URL", "http://127.0.0.1:9222")
    )
    flow_web_url: str = Field(
        default_factory=lambda: os.getenv("FLOW_WEB_URL", "https://labs.google/fx/tools/flow")
    )
    flow_timeout_sec: int = Field(
        default_factory=lambda: int(os.getenv("FLOW_TIMEOUT_SEC", "240"))
    )
    flow_mix_native_audio: bool = True

    # OpenAI / OpenAI-Compatible (DeepSeek / Qwen / Ark / Local vLLM)
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = Field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    openai_llm_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_LLM_MODEL", "gpt-4o")
    )
    openai_image_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    )

    # Google Gemini / Imagen
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_llm_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")
    )
    gemini_image_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_IMAGE_MODEL", "imagen-3.0-generate-002")
    )

    # Volcengine Ark (即梦 Seedream / Seedance / Doubao)
    volc_api_key: str = Field(default_factory=lambda: os.getenv("VOLC_API_KEY", ""))
    volc_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "VOLC_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
        )
    )
    volc_llm_model: str = Field(
        default_factory=lambda: os.getenv("VOLC_LLM_MODEL", "doubao-1-5-pro-32k-250115")
    )
    volc_image_model: str = Field(
        default_factory=lambda: os.getenv("VOLC_IMAGE_MODEL", "doubao-seedream-3-0-t2i-250415")
    )
    volc_video_model: str = Field(
        default_factory=lambda: os.getenv("VOLC_VIDEO_MODEL", "doubao-seedance-1-0-pro-250528")
    )

    # Alibaba Cloud Bailian / DashScope (通义万相 Wanx / Qwen)
    dashscope_api_key: str = Field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY", ""))
    dashscope_image_model: str = Field(
        default_factory=lambda: os.getenv("DASHSCOPE_IMAGE_MODEL", "wanx2.1-t2i-turbo")
    )
    dashscope_video_model: str = Field(
        default_factory=lambda: os.getenv("DASHSCOPE_VIDEO_MODEL", "wan2.1-i2v-turbo")
    )

    # Kuaishou Kling (可灵 Kolors / Kling)
    kling_access_key: str = Field(default_factory=lambda: os.getenv("KLING_ACCESS_KEY", ""))
    kling_secret_key: str = Field(default_factory=lambda: os.getenv("KLING_SECRET_KEY", ""))
    kling_base_url: str = Field(
        default_factory=lambda: os.getenv("KLING_BASE_URL", "https://api.klingai.com")
    )
    kling_image_model: str = Field(
        default_factory=lambda: os.getenv("KLING_IMAGE_MODEL", "kolors")
    )
    kling_video_model: str = Field(
        default_factory=lambda: os.getenv("KLING_VIDEO_MODEL", "kling-v1-6")
    )

    # Studio QA & Circuit Breaker Policy
    qa_pass_threshold: int = 75
    max_qa_retries_per_shot: int = 2
    max_concurrency: int = 4

    def masked_dict(self) -> dict:
        """Return safe dictionary with masked API secrets for frontend display."""
        raw = self.model_dump()
        for key in (
            "openai_api_key",
            "gemini_api_key",
            "volc_api_key",
            "dashscope_api_key",
            "kling_access_key",
            "kling_secret_key",
        ):
            val = raw.get(key, "")
            if val and len(val) > 8:
                raw[key] = f"{val[:4]}****{val[-4:]}"
            elif val:
                raw[key] = "****"
        return raw


_GLOBAL_SETTINGS = ProviderSettings()


def get_settings() -> ProviderSettings:
    return _GLOBAL_SETTINGS


def update_settings(patch: dict) -> ProviderSettings:
    global _GLOBAL_SETTINGS
    merged = _GLOBAL_SETTINGS.model_dump()
    for k, v in patch.items():
        if k in merged and v is not None:
            # Skip masked placeholders sent back unchanged from UI
            if isinstance(v, str) and "****" in v:
                continue
            merged[k] = v
    _GLOBAL_SETTINGS = ProviderSettings(**merged)
    return _GLOBAL_SETTINGS
