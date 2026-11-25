"""Abstract provider interfaces and async task polling utilities."""

from __future__ import annotations

import abc
import asyncio
import base64
import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, Optional
from pydantic import BaseModel, Field


class ReferenceImage(BaseModel):
    """Visual anchor passed into multi-reference T2I / I2V models."""

    role: Literal["character_turnaround", "scene_master_plate", "start_keyframe_anchor"]
    path: Path
    label: str = ""
    weight: float = 0.85

    def to_base64_data_uri(self) -> str:
        raw = self.path.read_bytes()
        ext = self.path.suffix.lower().lstrip(".") or "png"
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"


class ImageGenRequest(BaseModel):
    """Unified request contract for turnaround sheets, scene plates, and keyframes."""

    kind: Literal["character_turnaround", "scene_plate", "storyboard_keyframe"]
    prompt: str
    negative_prompt: str = ""
    width: int = 720
    height: int = 1280
    output_path: Path
    reference_images: list[ReferenceImage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseLLMProvider(abc.ABC):
    """Unified structured text & multimodal vision inspection interface."""

    vendor_name: str = "base"

    @abc.abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Generate structured JSON dictionary from system & user instructions."""

    @abc.abstractmethod
    async def inspect_images_json(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: list[Path],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Perform multimodal cross-image inspection (Tri-Image Reference Diffing)."""


class BaseImageProvider(abc.ABC):
    """Unified Text-to-Image & Multi-Reference Image Generation interface."""

    vendor_name: str = "base"

    @abc.abstractmethod
    async def generate_image(self, req: ImageGenRequest) -> Path:
        """Render image to req.output_path and return the saved Path."""


class BaseVideoProvider(abc.ABC):
    """Phase 2 interface for single-frame I2V and first-last-frame KF2V."""

    vendor_name: str = "base"

    @abc.abstractmethod
    async def generate_video(
        self,
        prompt: str,
        start_image: Path,
        output_path: Path,
        end_image: Optional[Path] = None,
        duration_sec: float = 5.0,
        motion_intensity: int = 5,
    ) -> Path:
        """Submit async video generation task, poll until completion, and save MP4."""


class BaseTTSProvider(abc.ABC):
    """Phase 2 interface for character-locked zero-shot TTS."""

    vendor_name: str = "base"

    @abc.abstractmethod
    async def synthesize_speech(
        self,
        text: str,
        voice_anchor_id: str,
        output_path: Path,
        acting_markup: str = "",
    ) -> Path:
        """Synthesize voiceover audio file to output_path."""


def extract_json_object(raw_text: str) -> dict[str, Any]:
    """Robustly parse JSON object from LLM markdown fence or raw output."""
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace : last_brace + 1]
    return json.loads(cleaned)


async def poll_async_task(
    check_fn: Callable[[], Awaitable[tuple[str, Any]]],
    timeout_sec: float = 300.0,
    initial_interval: float = 2.0,
    max_interval: float = 8.0,
) -> Any:
    """Exponential-backoff poller for commercial async T2I / I2V tasks."""
    elapsed = 0.0
    interval = initial_interval
    while elapsed < timeout_sec:
        status, payload = await check_fn()
        norm = status.lower()
        if norm in ("succeeded", "success", "completed", "done"):
            return payload
        if norm in ("failed", "error", "canceled", "cancelled"):
            raise RuntimeError(f"Async generation task failed: {payload}")
        await asyncio.sleep(interval)
        elapsed += interval
        interval = min(max_interval, interval * 1.35)
    raise TimeoutError(f"Async generation task timed out after {timeout_sec}s")
