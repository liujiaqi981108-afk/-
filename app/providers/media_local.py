"""Phase 2 Video & Neural/Procedural TTS Providers (Local Mock PyAV Video, Edge-TTS, and Commercial I2V)."""

from __future__ import annotations

import base64
import fractions
import math
import re
import wave
from pathlib import Path
from typing import Any, Optional

import av
import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from app.providers.base import BaseTTSProvider, BaseVideoProvider, poll_async_task
from app.providers.commercial import build_kling_jwt


def _crop_parallax(
    src_img: Image.Image, width: int, height: int, zoom: float, pan_x: float, pan_y: float
) -> Image.Image:
    iw, ih = src_img.size
    target_aspect = width / height
    src_aspect = iw / ih
    if src_aspect > target_aspect:
        base_h = ih
        base_w = int(ih * target_aspect)
    else:
        base_w = iw
        base_h = int(iw / target_aspect)

    cw = base_w / max(1.0, zoom)
    ch = base_h / max(1.0, zoom)
    max_dx = max(0.0, (iw - cw) / 2.0)
    max_dy = max(0.0, (ih - ch) / 2.0)
    cx = (iw / 2.0) + pan_x * max_dx
    cy = (ih / 2.0) + pan_y * max_dy
    box = (cx - cw / 2.0, cy - ch / 2.0, cx + cw / 2.0, cy + ch / 2.0)
    return src_img.resize((width, height), resample=Image.Resampling.BICUBIC, box=box)


class MockVideoProvider(BaseVideoProvider):
    """Offline PyAV H.264 + AAC clip synthesizer supporting both single-frame I2V and dual-frame KF2V."""

    vendor_name = "mock"

    async def generate_video(
        self,
        prompt: str,
        start_image: Path,
        output_path: Path,
        end_image: Optional[Path] = None,
        duration_sec: float = 4.0,
        motion_intensity: int = 5,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fps = 24
        sr = 44100
        dur = max(1.5, min(6.0, float(duration_sec)))
        total_frames = max(24, int(round(dur * fps)))

        s_img = Image.open(start_image).convert("RGB")
        w0, h0 = s_img.size
        # Ensure even H.264 dimensions matching aspect orientation
        if h0 >= w0:
            width, height = 720, 1280
        else:
            width, height = 1280, 720

        e_img = Image.open(end_image).convert("RGB") if (end_image and end_image.exists()) else None
        rng = np.random.default_rng(abs(hash(prompt)) % (2**31 - 1))
        particles = [
            [rng.uniform(0, width), rng.uniform(0, height), rng.uniform(1.8, 4.8), rng.uniform(1.4, 3.0)]
            for _ in range(30)
        ]

        out = av.open(str(output_path), mode="w")
        v_stream = out.add_stream("libx264", rate=fps)
        v_stream.width = width
        v_stream.height = height
        v_stream.pix_fmt = "yuv420p"
        v_stream.options = {"crf": "22", "preset": "ultrafast"}

        a_stream = out.add_stream("aac", rate=sr)
        a_stream.layout = "stereo"

        amp = 0.04 + 0.012 * max(1, min(10, motion_intensity))
        for f_idx in range(total_frames):
            u = f_idx / max(1, total_frames - 1)
            smooth_u = u * u * (3.0 - 2.0 * u)

            if e_img is not None:
                f_a = _crop_parallax(s_img, width, height, 1.02 + amp * smooth_u, 0.14 * smooth_u, -0.05 * smooth_u)
                f_b = _crop_parallax(
                    e_img, width, height, 1.02 + amp * (1.0 - smooth_u), -0.10 * (1.0 - smooth_u), 0.0
                )
                frame = Image.blend(f_a, f_b, smooth_u)
                if 0.42 <= u <= 0.54:
                    # Action impact specular flash on KF2V apex
                    boost = 1.0 + 0.24 * (1.0 - abs(u - 0.48) / 0.06)
                    frame = ImageEnhance.Brightness(frame).enhance(boost)
            else:
                zoom = 1.02 + amp * smooth_u
                pan_x = -0.18 + 0.36 * smooth_u
                pan_y = -0.06 * math.sin(math.pi * smooth_u)
                frame = _crop_parallax(s_img, width, height, zoom, pan_x, pan_y)

            # Atmospheric drifting snow / embers + moving specular light sweep
            rgba = frame.convert("RGBA")
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            drw = ImageDraw.Draw(overlay)
            sweep_x = int((0.15 + 0.70 * smooth_u) * width)
            drw.polygon(
                [(sweep_x - 36, 0), (sweep_x + 36, 0), (sweep_x - 90, height), (sweep_x - 162, height)],
                fill=(255, 224, 175, 16),
            )
            for pt in particles:
                pt[0] = (pt[0] + pt[2] * 0.9) % width
                pt[1] = (pt[1] + pt[2] * 2.3) % height
                r = pt[3]
                drw.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=(238, 245, 255, 145))

            composed = Image.alpha_composite(rgba, overlay).convert("RGB")
            vf = av.VideoFrame.from_image(composed)
            for pkt in v_stream.encode(vf):
                out.mux(pkt)

        for pkt in v_stream.encode(None):
            out.mux(pkt)

        # Native clip environmental audio bed (simulating Google Flow Veo native audio stream)
        n_samples = int(round(dur * sr))
        noise = rng.normal(0.0, 0.04, n_samples).astype(np.float32)
        wind = np.convolve(noise, np.ones(64, dtype=np.float32) / 64.0, mode="same")
        stereo = np.vstack([wind, np.roll(wind, 320)]).astype(np.float32)

        chunk_size = 1024
        pts = 0
        for s in range(0, n_samples, chunk_size):
            chunk = np.ascontiguousarray(stereo[:, s : s + chunk_size], dtype=np.float32)
            af = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
            af.sample_rate = sr
            af.pts = pts
            af.time_base = fractions.Fraction(1, sr)
            pts += chunk.shape[1]
            for pkt in a_stream.encode(af):
                out.mux(pkt)

        for pkt in a_stream.encode(None):
            out.mux(pkt)

        out.close()
        return output_path


class EdgeOrSynthTTSProvider(BaseTTSProvider):
    """Neural Chinese TTS via Microsoft `edge-tts` with zero-network procedural fallback."""

    def __init__(self, prefer_neural: bool = True) -> None:
        self.prefer_neural = prefer_neural
        self.vendor_name = "edge_tts" if prefer_neural else "mock"

    @staticmethod
    def _select_edge_voice(voice_anchor_id: str) -> tuple[str, str, str]:
        if "baritone" in voice_anchor_id or "male" in voice_anchor_id or "rival" in voice_anchor_id:
            return ("zh-CN-YunjianNeural", "-6%", "-8Hz")
        return ("zh-CN-XiaoxiaoNeural", "-10%", "-6Hz")

    @staticmethod
    def _synth_offline_wav(text: str, voice_anchor_id: str, output_path: Path) -> Path:
        sr = 44100
        clean = re.sub(r"\[.*?\]|<.*?>", "", text).strip() or "嗯"
        char_count = max(1, len([c for c in clean if not c.isspace()]))
        dur = min(4.2, max(0.75, char_count * 0.23))
        n = int(dur * sr)
        t = np.arange(n, dtype=np.float32) / sr
        f0 = 128.0 if "baritone" in voice_anchor_id else 208.0

        # Syllable envelope giving natural speech-like cadence for sidechain ducking & playback
        syllable_rate = max(2.8, char_count / dur)
        env = np.clip(0.55 + 0.45 * np.sin(2 * np.pi * syllable_rate * t), 0.08, 1.0)
        fade = min(int(0.06 * sr), n // 4)
        if fade > 0:
            env[:fade] *= np.linspace(0.0, 1.0, fade)
            env[-fade:] *= np.linspace(1.0, 0.0, fade)

        wave_f = (
            0.55 * np.sin(2 * np.pi * f0 * t)
            + 0.28 * np.sin(2 * np.pi * (f0 * 2.0) * t)
            + 0.12 * np.sin(2 * np.pi * (f0 * 3.0) * t)
        ) * env * 0.28

        wav_path = output_path.with_suffix(".wav")
        pcm16 = np.clip(wave_f * 32767.0, -32768, 32767).astype(np.int16)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm16.tobytes())
        if wav_path != output_path:
            output_path.write_bytes(wav_path.read_bytes())
        return output_path

    async def synthesize_speech(
        self,
        text: str,
        voice_anchor_id: str,
        output_path: Path,
        acting_markup: str = "",
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        clean_text = re.sub(r"\[.*?\]|<.*?>", "", text).strip()
        if not clean_text:
            return self._synth_offline_wav("……", voice_anchor_id, output_path)

        if self.prefer_neural:
            try:
                import edge_tts

                voice, rate, pitch = self._select_edge_voice(voice_anchor_id)
                mp3_target = output_path.with_suffix(".mp3")
                comm = edge_tts.Communicate(text=clean_text, voice=voice, rate=rate, pitch=pitch)
                await comm.save(str(mp3_target))
                if mp3_target.exists() and mp3_target.stat().st_size > 200:
                    if mp3_target != output_path:
                        output_path.write_bytes(mp3_target.read_bytes())
                    return output_path
            except Exception:
                pass

        return self._synth_offline_wav(clean_text, voice_anchor_id, output_path)


class VolcSeedanceVideoProvider(BaseVideoProvider):
    """Volcengine Ark Seedance 1.0 Pro I2V / First-Last-Frame KF2V adapter."""

    vendor_name = "volcengine"

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_video(
        self,
        prompt: str,
        start_image: Path,
        output_path: Path,
        end_image: Optional[Path] = None,
        duration_sec: float = 5.0,
        motion_intensity: int = 5,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        def _uri(p: Path) -> str:
            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{b64}"

        content: list[dict[str, Any]] = [
            {"type": "text", "text": f"{prompt} --duration {int(round(duration_sec))}"},
            {"type": "image_url", "image_url": {"url": _uri(start_image)}, "role": "first_frame"},
        ]
        if end_image and end_image.exists():
            content.append({"type": "image_url", "image_url": {"url": _uri(end_image)}, "role": "last_frame"})

        async with httpx.AsyncClient(timeout=180.0) as client:
            submit = await client.post(
                f"{self.base_url}/contents/generations/tasks",
                headers=headers,
                json={"model": self.model, "content": content},
            )
            submit.raise_for_status()
            task_id = submit.json()["id"]

            async def _check() -> tuple[str, Any]:
                r = await client.get(f"{self.base_url}/contents/generations/tasks/{task_id}", headers=headers)
                r.raise_for_status()
                d = r.json()
                return d.get("status", "running"), d

            res = await poll_async_task(_check, timeout_sec=360.0)
            video_url = res["content"]["video_url"]
            dl = await client.get(video_url)
            dl.raise_for_status()
            output_path.write_bytes(dl.content)
        return output_path


class DashScopeWanVideoProvider(BaseVideoProvider):
    """Alibaba Cloud Bailian Wan 2.1 I2V / KF2V async video adapter."""

    vendor_name = "dashscope"

    def __init__(self, api_key: str, model: str = "wan2.1-i2v-turbo") -> None:
        self.api_key = api_key
        self.model = model

    async def generate_video(
        self,
        prompt: str,
        start_image: Path,
        output_path: Path,
        end_image: Optional[Path] = None,
        duration_sec: float = 5.0,
        motion_intensity: int = 5,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        img_uri = f"data:image/png;base64,{base64.b64encode(start_image.read_bytes()).decode('ascii')}"
        inp: dict[str, Any] = {"prompt": prompt, "img_url": img_uri}
        if end_image and end_image.exists():
            inp["tail_img_url"] = f"data:image/png;base64,{base64.b64encode(end_image.read_bytes()).decode('ascii')}"

        async with httpx.AsyncClient(timeout=180.0) as client:
            submit = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis",
                headers=headers,
                json={"model": self.model, "input": inp},
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

            res = await poll_async_task(_check, timeout_sec=360.0)
            dl = await client.get(res["video_url"])
            dl.raise_for_status()
            output_path.write_bytes(dl.content)
        return output_path


class KlingVideoProvider(BaseVideoProvider):
    """Kuaishou Kling v1.6 I2V + Start/End Frame (`image` + `image_tail`) video adapter."""

    vendor_name = "kling"

    def __init__(self, access_key: str, secret_key: str, base_url: str, model: str = "kling-v1-6") -> None:
        self.access_key = access_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_video(
        self,
        prompt: str,
        start_image: Path,
        output_path: Path,
        end_image: Optional[Path] = None,
        duration_sec: float = 5.0,
        motion_intensity: int = 5,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        token = build_kling_jwt(self.access_key, self.secret_key)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body: dict[str, Any] = {
            "model_name": self.model,
            "prompt": prompt[:2500],
            "image": base64.b64encode(start_image.read_bytes()).decode("ascii"),
            "duration": "5",
            "mode": "pro" if (end_image and end_image.exists()) else "std",
        }
        if end_image and end_image.exists():
            body["image_tail"] = base64.b64encode(end_image.read_bytes()).decode("ascii")

        async with httpx.AsyncClient(timeout=180.0) as client:
            submit = await client.post(f"{self.base_url}/v1/videos/image2video", headers=headers, json=body)
            submit.raise_for_status()
            task_id = submit.json()["data"]["task_id"]

            async def _check() -> tuple[str, Any]:
                r = await client.get(f"{self.base_url}/v1/videos/image2video/{task_id}", headers=headers)
                r.raise_for_status()
                d = r.json()["data"]
                return d["task_status"], d

            res = await poll_async_task(_check, timeout_sec=360.0)
            video_url = res["task_result"]["videos"][0]["url"]
            dl = await client.get(video_url)
            dl.raise_for_status()
            output_path.write_bytes(dl.content)
        return output_path
