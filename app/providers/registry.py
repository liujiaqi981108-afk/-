"""Runtime provider factory with hot-swappable vendor support and fallback safety."""

from __future__ import annotations

from typing import Optional

from app.config import ProviderSettings, get_settings
from app.providers.base import (
    BaseImageProvider,
    BaseLLMProvider,
    BaseTTSProvider,
    BaseVideoProvider,
)
from app.providers.commercial import (
    DashScopeWanxImageProvider,
    GeminiImagenProvider,
    GeminiLLMProvider,
    KlingImageProvider,
    OpenAICompatibleLLMProvider,
    OpenAIImageProvider,
)
from app.providers.flow_browser import GoogleFlowImageProvider, GoogleFlowVideoProvider
from app.providers.media_local import (
    DashScopeWanVideoProvider,
    EdgeOrSynthTTSProvider,
    KlingVideoProvider,
    MockVideoProvider,
    VolcSeedanceVideoProvider,
)
from app.providers.mock import MockImageProvider, MockLLMProvider


def get_llm_provider(settings: Optional[ProviderSettings] = None) -> BaseLLMProvider:
    cfg = settings or get_settings()
    vendor = cfg.llm_vendor
    if vendor == "openai" and cfg.openai_api_key:
        return OpenAICompatibleLLMProvider(
            api_key=cfg.openai_api_key,
            base_url=cfg.openai_base_url,
            model=cfg.openai_llm_model,
            vendor_name="openai",
        )
    if vendor == "volcengine" and cfg.volc_api_key:
        return OpenAICompatibleLLMProvider(
            api_key=cfg.volc_api_key,
            base_url=cfg.volc_base_url,
            model=cfg.volc_llm_model,
            vendor_name="volcengine",
        )
    if vendor == "dashscope" and cfg.dashscope_api_key:
        return OpenAICompatibleLLMProvider(
            api_key=cfg.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-max",
            vendor_name="dashscope",
        )
    if vendor == "gemini" and cfg.gemini_api_key:
        return GeminiLLMProvider(api_key=cfg.gemini_api_key, model=cfg.gemini_llm_model)
    return MockLLMProvider()


def get_image_provider(settings: Optional[ProviderSettings] = None) -> BaseImageProvider:
    cfg = settings or get_settings()
    vendor = cfg.image_vendor
    if vendor == "flow_browser":
        return GoogleFlowImageProvider(
            cdp_url=cfg.flow_cdp_url,
            flow_web_url=cfg.flow_web_url,
            timeout_sec=cfg.flow_timeout_sec,
        )
    if vendor == "openai" and cfg.openai_api_key:
        return OpenAIImageProvider(
            api_key=cfg.openai_api_key,
            base_url=cfg.openai_base_url,
            model=cfg.openai_image_model,
            vendor_name="openai",
        )
    if vendor == "volcengine" and cfg.volc_api_key:
        return OpenAIImageProvider(
            api_key=cfg.volc_api_key,
            base_url=cfg.volc_base_url,
            model=cfg.volc_image_model,
            vendor_name="volcengine",
        )
    if vendor == "gemini" and cfg.gemini_api_key:
        return GeminiImagenProvider(api_key=cfg.gemini_api_key, model=cfg.gemini_image_model)
    if vendor == "dashscope" and cfg.dashscope_api_key:
        return DashScopeWanxImageProvider(
            api_key=cfg.dashscope_api_key, model=cfg.dashscope_image_model
        )
    if vendor == "kling" and cfg.kling_access_key and cfg.kling_secret_key:
        return KlingImageProvider(
            access_key=cfg.kling_access_key,
            secret_key=cfg.kling_secret_key,
            base_url=cfg.kling_base_url,
            model=cfg.kling_image_model,
        )
    return MockImageProvider()


def get_video_provider(settings: Optional[ProviderSettings] = None) -> BaseVideoProvider:
    cfg = settings or get_settings()
    vendor = cfg.video_vendor
    if vendor == "flow_browser":
        return GoogleFlowVideoProvider(
            cdp_url=cfg.flow_cdp_url,
            flow_web_url=cfg.flow_web_url,
            timeout_sec=cfg.flow_timeout_sec,
        )
    if vendor == "volcengine" and cfg.volc_api_key:
        return VolcSeedanceVideoProvider(
            api_key=cfg.volc_api_key,
            base_url=cfg.volc_base_url,
            model=cfg.volc_video_model,
        )
    if vendor == "dashscope" and cfg.dashscope_api_key:
        return DashScopeWanVideoProvider(
            api_key=cfg.dashscope_api_key,
            model=cfg.dashscope_video_model,
        )
    if vendor == "kling" and cfg.kling_access_key and cfg.kling_secret_key:
        return KlingVideoProvider(
            access_key=cfg.kling_access_key,
            secret_key=cfg.kling_secret_key,
            base_url=cfg.kling_base_url,
            model=cfg.kling_video_model,
        )
    return MockVideoProvider()


def get_tts_provider(settings: Optional[ProviderSettings] = None) -> BaseTTSProvider:
    cfg = settings or get_settings()
    if cfg.tts_vendor == "mock":
        return EdgeOrSynthTTSProvider(prefer_neural=False)
    return EdgeOrSynthTTSProvider(prefer_neural=True)
