"""Local Chrome CDP Web Automation Provider for Google Flow (Nano Banana & Veo / Omni Flash)."""

from __future__ import annotations

import asyncio
import base64
import io
import json
from pathlib import Path
from typing import Any, Optional

import httpx
from PIL import Image

from app.providers.base import BaseImageProvider, BaseVideoProvider, ImageGenRequest

SELECTORS_PATH = Path(__file__).resolve().parent / "flow_selectors.json"
_FLOW_BROWSER_LOCK = asyncio.Lock()


class FlowManualInterventionRequiredError(RuntimeError):
    """Raised when the user must manually sign in or complete verification in their Chrome window."""


def load_flow_selectors() -> dict[str, list[str]]:
    return json.loads(SELECTORS_PATH.read_text(encoding="utf-8"))


async def check_flow_cdp_status(
    cdp_url: str = "http://127.0.0.1:9222",
    flow_web_url: str = "https://labs.google/fx/tools/flow",
) -> dict[str, Any]:
    """Non-intrusive check of the user's local Chrome `--remote-debugging-port` session."""
    base = cdp_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=1.8) as client:
            ver_resp = await client.get(f"{base}/json/version")
            ver_resp.raise_for_status()
            ver_info = ver_resp.json()

            tabs_resp = await client.get(f"{base}/json/list")
            tabs = tabs_resp.json() if tabs_resp.status_code == 200 else []
    except Exception as exc:
        return {
            "connected": False,
            "browser": "",
            "flow_tab_open": False,
            "login_required_hint": False,
            "open_tabs": 0,
            "cdp_url": base,
            "flow_web_url": flow_web_url,
            "message": (
                f"未检测到本地 Chrome 调试端口 ({base})。"
                "请在本机终端运行 `python scripts/launch_local_chrome.py` 启动专属 Chrome 窗口并登录 Google Flow。"
            ),
            "error": str(exc),
        }

    page_tabs = [t for t in tabs if t.get("type") == "page"]
    urls = [str(t.get("url") or "") for t in page_tabs]
    flow_open = any(("labs.google" in u and "flow" in u) or ("flow.google" in u) for u in urls)
    login_hint = any("accounts.google.com" in u for u in urls)

    if login_hint:
        msg = "已连上本地 Chrome，但检测到当前处于 Google 登录页。请先在弹出的 Chrome 窗口手动完成账号登录。"
    elif flow_open:
        msg = "✅ 已成功挂载本地 Chrome (Google Flow 标签页在线)，可直接免 API Key 调用 Nano Banana 与 Flow 视频！"
    else:
        msg = "已连上本地 Chrome，首次生成时将自动在浏览器中打开 Google Flow 工作台。"

    return {
        "connected": True,
        "browser": ver_info.get("Browser", "Chrome"),
        "flow_tab_open": flow_open,
        "login_required_hint": login_hint,
        "open_tabs": len(page_tabs),
        "cdp_url": base,
        "flow_web_url": flow_web_url,
        "message": msg,
    }


async def _abort_if_manual_gate_present(page: Any) -> None:
    """Strictly stop and ask the user to act manually if sign-in or human verification appears."""
    url = (page.url or "").lower()
    if "accounts.google.com" in url or "/signin" in url:
        raise FlowManualInterventionRequiredError(
            "检测到 Google 账号未登录：请在本地弹出的 Chrome 窗口中手动完成 Google 登录并进入 Flow 项目页后，再点击重试。"
        )

    # Check for anti-bot / CAPTCHA / human verification iframes or prompts — NEVER interact with them!
    gate_frames = await page.locator(
        "iframe[src*='recaptcha' i], iframe[src*='hcaptcha' i], iframe[src*='turnstile' i]"
    ).count()
    if gate_frames > 0:
        raise FlowManualInterventionRequiredError(
            "检测到页面出现人机验证组件：系统严格遵循安全规范不做任何自动点击，请在本地 Chrome 窗口手动确认后再重试。"
        )

    body_snippet = ""
    try:
        body_snippet = (await page.locator("body").inner_text(timeout=1500))[:1200].lower()
    except Exception:
        pass

    if "sign in with google" in body_snippet and "new project" not in body_snippet and "generate" not in body_snippet:
        raise FlowManualInterventionRequiredError(
            "Google Flow 当前处于未登录欢迎页：请在本地 Chrome 窗口手动点击登录你的 Google 账号后再重试。"
        )
    if any(k in body_snippet for k in ("verify you are human", "unusual traffic", "进行人机身份验证")):
        raise FlowManualInterventionRequiredError(
            "检测到安全验证提示：请在本地 Chrome 窗口手动处理完成后再重试。"
        )


async def _click_first_visible(page: Any, selectors: list[str], timeout_ms: int = 1200) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=timeout_ms)
                await page.wait_for_timeout(450)
                return True
        except Exception:
            continue
    return False


async def _ensure_flow_workspace(page: Any, flow_web_url: str, selectors: dict[str, list[str]]) -> None:
    cur = page.url or ""
    if not (("labs.google" in cur and "flow" in cur) or ("flow.google" in cur)):
        await page.goto(flow_web_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1800)

    await _abort_if_manual_gate_present(page)

    # If on the Flow dashboard rather than inside an editor with a prompt box, enter/create a project
    has_prompt = False
    for psel in selectors["prompt_inputs"]:
        if await page.locator(psel).count() > 0:
            has_prompt = True
            break

    if not has_prompt:
        clicked = await _click_first_visible(page, selectors["new_project_triggers"], timeout_ms=2500)
        if clicked:
            await page.wait_for_timeout(2000)
        await _abort_if_manual_gate_present(page)


async def _upload_file_via_slot_or_input(
    page: Any,
    file_path: Path,
    slot_selectors: list[str],
    fallback_input_index: int = 0,
) -> bool:
    """Upload a local image either via a slot button triggering filechooser or direct input[type=file]."""
    for sel in slot_selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                async with page.expect_file_chooser(timeout=2500) as fc_info:
                    await loc.click(timeout=1500)
                chooser = await fc_info.value
                await chooser.set_files(str(file_path))
                await page.wait_for_timeout(900)
                return True
        except Exception:
            continue

    # Fallback to direct hidden <input type="file">
    file_inputs = page.locator("input[type='file']")
    count = await file_inputs.count()
    if count > 0:
        idx = min(fallback_input_index, count - 1)
        await file_inputs.nth(idx).set_input_files(str(file_path))
        await page.wait_for_timeout(900)
        return True
    return False


async def _fill_prompt_and_submit(
    page: Any, prompt: str, selectors: dict[str, list[str]]
) -> None:
    filled = False
    for sel in selectors["prompt_inputs"]:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=1500)
                await loc.fill(prompt)
                filled = True
                break
        except Exception:
            continue

    if not filled:
        raise FlowManualInterventionRequiredError(
            "未能在当前 Google Flow 页面定位到提示词输入框。请确认 Chrome 窗口已进入某个 Flow 项目编辑界面后再试。"
        )

    await page.wait_for_timeout(350)
    clicked = await _click_first_visible(page, selectors["generate_buttons"], timeout_ms=2000)
    if not clicked:
        await page.keyboard.press("Enter")


async def _fetch_media_src_bytes_in_page(page: Any, src_url: str) -> Optional[bytes]:
    """Fetch blob: or authenticated https: media URL directly inside the logged-in browser context."""
    b64_data = await page.evaluate(
        """async (url) => {
            try {
                const res = await fetch(url);
                if (!res.ok) return null;
                const buf = await res.arrayBuffer();
                const bytes = new Uint8Array(buf);
                let binary = '';
                const chunk = 0x8000;
                for (let i = 0; i < bytes.length; i += chunk) {
                    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
                }
                return btoa(binary);
            } catch (e) {
                return null;
            }
        }""",
        src_url,
    )
    if not b64_data:
        return None
    return base64.b64decode(b64_data)


class GoogleFlowImageProvider(BaseImageProvider):
    """Drives Google Flow's built-in Nano Banana model via local Chrome CDP (with reference images)."""

    vendor_name = "flow_browser"

    def __init__(
        self,
        cdp_url: str = "http://127.0.0.1:9222",
        flow_web_url: str = "https://labs.google/fx/tools/flow",
        timeout_sec: int = 180,
    ) -> None:
        self.cdp_url = cdp_url
        self.flow_web_url = flow_web_url
        self.timeout_sec = timeout_sec

    async def generate_image(self, req: ImageGenRequest) -> Path:
        status = await check_flow_cdp_status(self.cdp_url, self.flow_web_url)
        if not status["connected"]:
            raise FlowManualInterventionRequiredError(status["message"])

        from playwright.async_api import async_playwright

        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        selectors = load_flow_selectors()

        async with _FLOW_BROWSER_LOCK:
            pw = await async_playwright().start()
            try:
                browser = await pw.chromium.connect_over_cdp(self.cdp_url)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = next(
                    (
                        p
                        for p in context.pages
                        if ("labs.google" in p.url and "flow" in p.url) or ("flow.google" in p.url)
                    ),
                    context.pages[0] if context.pages else await context.new_page(),
                )

                await _ensure_flow_workspace(page, self.flow_web_url, selectors)
                await _click_first_visible(page, selectors["image_mode_triggers"])

                # Upload up to 3 reference images (Character 3-View + Scene Master Plate)
                for idx, ref in enumerate(req.reference_images[:3]):
                    if ref.path.exists():
                        await _upload_file_via_slot_or_input(
                            page,
                            ref.path,
                            selectors["reference_upload_triggers"],
                            fallback_input_index=idx,
                        )

                captured_images: list[bytes] = []

                async def _on_response(resp: Any) -> None:
                    try:
                        ct = (resp.headers.get("content-type") or "").lower()
                        if resp.status == 200 and any(t in ct for t in ("image/png", "image/jpeg", "image/webp")):
                            body = await resp.body()
                            if len(body) >= 24_000:
                                captured_images.append(body)
                    except Exception:
                        pass

                existing_imgs = set(
                    await page.evaluate(
                        "() => Array.from(document.querySelectorAll('img')).map(el => el.src).filter(Boolean)"
                    )
                )

                page.on("response", _on_response)
                try:
                    full_prompt = req.prompt
                    if req.negative_prompt:
                        full_prompt += f"\nAvoid strictly: {req.negative_prompt}"
                    await _fill_prompt_and_submit(page, full_prompt, selectors)

                    elapsed = 0.0
                    raw_bytes: Optional[bytes] = None
                    while elapsed < self.timeout_sec:
                        await _abort_if_manual_gate_present(page)
                        if captured_images:
                            raw_bytes = captured_images[-1]
                            break

                        cur_imgs: list[dict[str, Any]] = await page.evaluate(
                            """() => Array.from(document.querySelectorAll('img'))
                                .filter(el => el.complete && el.naturalWidth >= 512)
                                .map(el => ({src: el.src, w: el.naturalWidth, h: el.naturalHeight}))"""
                        )
                        new_candidates = [i for i in cur_imgs if i["src"] and i["src"] not in existing_imgs]
                        if new_candidates:
                            fetched = await _fetch_media_src_bytes_in_page(page, new_candidates[-1]["src"])
                            if fetched and len(fetched) >= 20_000:
                                raw_bytes = fetched
                                break

                        await asyncio.sleep(2.0)
                        elapsed += 2.0

                    if not raw_bytes:
                        raise TimeoutError(
                            f"等待 Google Flow (Nano Banana) 出图超时 ({self.timeout_sec}s)。请检查本地 Chrome 窗口生成状态。"
                        )

                    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                    img.save(req.output_path, format="PNG")
                    return req.output_path
                finally:
                    page.remove_listener("response", _on_response)
            finally:
                await pw.stop()


class GoogleFlowVideoProvider(BaseVideoProvider):
    """Drives Google Flow `Video > Frames` (Omni Flash / Veo) via local Chrome CDP for I2V & KF2V."""

    vendor_name = "flow_browser"

    def __init__(
        self,
        cdp_url: str = "http://127.0.0.1:9222",
        flow_web_url: str = "https://labs.google/fx/tools/flow",
        timeout_sec: int = 240,
    ) -> None:
        self.cdp_url = cdp_url
        self.flow_web_url = flow_web_url
        self.timeout_sec = timeout_sec

    async def generate_video(
        self,
        prompt: str,
        start_image: Path,
        output_path: Path,
        end_image: Optional[Path] = None,
        duration_sec: float = 5.0,
        motion_intensity: int = 5,
    ) -> Path:
        status = await check_flow_cdp_status(self.cdp_url, self.flow_web_url)
        if not status["connected"]:
            raise FlowManualInterventionRequiredError(status["message"])

        from playwright.async_api import async_playwright

        output_path.parent.mkdir(parents=True, exist_ok=True)
        selectors = load_flow_selectors()

        async with _FLOW_BROWSER_LOCK:
            pw = await async_playwright().start()
            try:
                browser = await pw.chromium.connect_over_cdp(self.cdp_url)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = next(
                    (
                        p
                        for p in context.pages
                        if ("labs.google" in p.url and "flow" in p.url) or ("flow.google" in p.url)
                    ),
                    context.pages[0] if context.pages else await context.new_page(),
                )

                await _ensure_flow_workspace(page, self.flow_web_url, selectors)
                await _click_first_visible(page, selectors["video_mode_triggers"])
                await _click_first_visible(page, selectors["frames_submode_triggers"])

                if start_image.exists():
                    await _upload_file_via_slot_or_input(
                        page, start_image, selectors["start_frame_triggers"], fallback_input_index=0
                    )
                if end_image and end_image.exists():
                    await _upload_file_via_slot_or_input(
                        page, end_image, selectors["end_frame_triggers"], fallback_input_index=1
                    )

                captured_videos: list[bytes] = []

                async def _on_response(resp: Any) -> None:
                    try:
                        ct = (resp.headers.get("content-type") or "").lower()
                        if resp.status in (200, 206) and ("video/mp4" in ct or resp.url.endswith(".mp4")):
                            body = await resp.body()
                            if len(body) >= 65_000:
                                captured_videos.append(body)
                    except Exception:
                        pass

                existing_vids = set(
                    await page.evaluate(
                        """() => Array.from(document.querySelectorAll('video'))
                            .map(v => v.currentSrc || v.src)
                            .filter(Boolean)"""
                    )
                )

                page.on("response", _on_response)
                try:
                    await _fill_prompt_and_submit(page, prompt, selectors)

                    elapsed = 0.0
                    mp4_bytes: Optional[bytes] = None
                    while elapsed < self.timeout_sec:
                        await _abort_if_manual_gate_present(page)
                        if captured_videos:
                            mp4_bytes = captured_videos[-1]
                            break

                        cur_vids: list[str] = await page.evaluate(
                            """() => Array.from(document.querySelectorAll('video'))
                                .map(v => v.currentSrc || v.src)
                                .filter(Boolean)"""
                        )
                        new_vids = [u for u in cur_vids if u not in existing_vids]
                        if new_vids:
                            fetched = await _fetch_media_src_bytes_in_page(page, new_vids[-1])
                            if fetched and len(fetched) >= 65_000:
                                mp4_bytes = fetched
                                break

                        await asyncio.sleep(3.0)
                        elapsed += 3.0

                    if not mp4_bytes:
                        raise TimeoutError(
                            f"等待 Google Flow 生成视频超时 ({self.timeout_sec}s)。"
                            "若 Flow 页面已生成完毕，你也可以点击下载并在工作台『手动上传 .mp4 片段』直接合片。"
                        )

                    output_path.write_bytes(mp4_bytes)
                    return output_path
                finally:
                    page.remove_listener("response", _on_response)
            finally:
                await pw.stop()
