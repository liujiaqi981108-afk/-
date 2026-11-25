"""Production async REST adapters for OpenAI, Gemini, Volcengine Seedream, DashScope Wanx, and Kling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any, Optional
import httpx

from app.config import ProviderSettings
from app.providers.base import (
    BaseImageProvider,
    BaseLLMProvider,
    ImageGenRequest,
    extract_json_object,
    poll_async_task,
)


def build_kling_jwt(access_key: str, secret_key: str, ttl_sec: int = 1800) -> str:
    """Sign HS256 JWT token for Kuaishou Kling API using stdlib hmac/hashlib."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"iss": access_key, "exp": now + ttl_sec, "nbf": now - 5}

    def _b64url(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    signing_input = f"{_b64url(header)}.{_b64url(payload)}"
    sig = hmac.new(secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{signing_input}.{sig_b64}"


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    """Supports OpenAI, DeepSeek, Volcengine Ark Chat, Bailian Qwen, and local vLLM."""

    def __init__(self, api_key: str, base_url: str, model: str, vendor_name: str = "openai") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vendor_name = vendor_name

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        sys_full = system_prompt
        if schema_hint:
            sys_full += f"\n\n请严格只输出合法 JSON 对象，结构参考：\n{schema_hint}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_full},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return extract_json_object(content)

    async def inspect_images_json(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: list[Path],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        user_parts: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for p in image_paths:
            if p.exists():
                b64 = base64.b64encode(p.read_bytes()).decode("ascii")
                user_parts.append(
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                )
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt + "\n请只输出合法 JSON 对象。"},
                {"role": "user", "content": user_parts},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return extract_json_object(content)


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini native REST adapter for structured JSON and Tri-Image VLM QA."""

    vendor_name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key
        self.model = model

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        prompt_text = user_prompt if not schema_hint else f"{user_prompt}\n\nJSON Schema Hint:\n{schema_hint}"
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, params={"key": self.api_key}, json=body)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return extract_json_object(text)

    async def inspect_images_json(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: list[Path],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        parts: list[dict[str, Any]] = [{"text": user_prompt}]
        for p in image_paths:
            if p.exists():
                parts.append(
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": base64.b64encode(p.read_bytes()).decode("ascii"),
                        }
                    }
                )
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, params={"key": self.api_key}, json=body)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return extract_json_object(text)


class OpenAIImageProvider(BaseImageProvider):
    """Supports OpenAI gpt-image-1 / dall-e-3 and OpenAI-compatible image endpoints."""

    def __init__(self, api_key: str, base_url: str, model: str, vendor_name: str = "openai") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vendor_name = vendor_name

    async def generate_image(self, req: ImageGenRequest) -> Path:
        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        size = "1024x1536" if req.height > req.width else ("1536x1024" if req.width > req.height else "1024x1024")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        full_prompt = req.prompt
        if req.negative_prompt:
            full_prompt += f"\nAvoid strictly: {req.negative_prompt}"

        payload: dict[str, Any] = {"model": self.model, "prompt": full_prompt, "size": size, "n": 1}
        # Volcengine Seedream supports subject/scene reference image conditioning via `image`
        if self.vendor_name == "volcengine" and req.reference_images:
            payload["image"] = req.reference_images[0].to_base64_data_uri()

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self.base_url}/images/generations", headers=headers, json=payload)
            resp.raise_for_status()
            item = resp.json()["data"][0]
            if "b64_json" in item and item["b64_json"]:
                req.output_path.write_bytes(base64.b64decode(item["b64_json"]))
            elif "url" in item and item["url"]:
                dl = await client.get(item["url"])
                dl.raise_for_status()
                req.output_path.write_bytes(dl.content)
            else:
                raise RuntimeError(f"Unexpected image response payload: {item}")
        return req.output_path


class GeminiImagenProvider(BaseImageProvider):
    """Google Imagen 3 REST adapter."""

    vendor_name = "gemini"

    def __init__(self, api_key: str, model: str = "imagen-3.0-generate-002") -> None:
        self.api_key = api_key
        self.model = model

    async def generate_image(self, req: ImageGenRequest) -> Path:
        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        aspect = "9:16" if req.height > req.width else ("16:9" if req.width > req.height else "4:3")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:predict"
        body = {
            "instances": [{"prompt": req.prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": aspect},
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, params={"key": self.api_key}, json=body)
            resp.raise_for_status()
            b64 = resp.json()["predictions"][0]["bytesBase64Encoded"]
            req.output_path.write_bytes(base64.b64decode(b64))
        return req.output_path


class DashScopeWanxImageProvider(BaseImageProvider):
    """Alibaba Cloud Tongyi Wanx 2.1 async T2I adapter."""

    vendor_name = "dashscope"

    def __init__(self, api_key: str, model: str = "wanx2.1-t2i-turbo") -> None:
        self.api_key = api_key
        self.model = model

    async def generate_image(self, req: ImageGenRequest) -> Path:
        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        size = "720*1280" if req.height > req.width else "1280*720"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        body = {
            "model": self.model,
            "input": {"prompt": req.prompt, "negative_prompt": req.negative_prompt},
            "parameters": {"size": size, "n": 1},
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            submit = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                headers=headers,
                json=body,
            )
            submit.raise_for_status()
            task_id = submit.json()["output"]["task_id"]

            async def _check() -> tuple[str, Any]:
                r = await client.get(
                    f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                r.raise_for_status()
                out = r.json()["output"]
                return out["task_status"], out

            result = await poll_async_task(_check)
            img_url = result["results"][0]["url"]
            dl = await client.get(img_url)
            dl.raise_for_status()
            req.output_path.write_bytes(dl.content)
        return req.output_path


class KlingImageProvider(BaseImageProvider):
    """Kuaishou Kling (Kolors) async T2I adapter with subject reference support."""

    vendor_name = "kling"

    def __init__(self, access_key: str, secret_key: str, base_url: str, model: str = "kolors") -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_image(self, req: ImageGenRequest) -> Path:
        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        token = build_kling_jwt(self.access_key, self.secret_key)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        aspect = "9:16" if req.height > req.width else ("16:9" if req.width > req.height else "3:2")
        body: dict[str, Any] = {
            "model_name": self.model,
            "prompt": req.prompt[:2500],
            "negative_prompt": req.negative_prompt[:1000],
            "aspect_ratio": aspect,
            "n": 1,
        }
        if req.reference_images:
            ref_bytes = req.reference_images[0].path.read_bytes()
            body["image"] = base64.b64encode(ref_bytes).decode("ascii")
            body["image_reference"] = "subject"
            body["image_fidelity"] = req.reference_images[0].weight

        async with httpx.AsyncClient(timeout=180.0) as client:
            submit = await client.post(f"{self.base_url}/v1/images/generations", headers=headers, json=body)
            submit.raise_for_status()
            task_id = submit.json()["data"]["task_id"]

            async def _check() -> tuple[str, Any]:
                r = await client.get(f"{self.base_url}/v1/images/generations/{task_id}", headers=headers)
                r.raise_for_status()
                d = r.json()["data"]
                return d["task_status"], d

            result = await poll_async_task(_check)
            img_url = result["task_result"]["images"][0]["url"]
            dl = await client.get(img_url)
            dl.raise_for_status()
            req.output_path.write_bytes(dl.content)
        return req.output_path
