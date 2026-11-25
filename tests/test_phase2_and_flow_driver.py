"""Phase 2 end-to-end tests: Flow CDP status/routing, video clip rendering, manual MP4 upload, and PyAV master muxing."""

from __future__ import annotations

from pathlib import Path
import av
import httpx
import pytest

from app.config import ProviderSettings, update_settings
from app.main import app
from app.models.schemas import WorkflowStage
from app.providers.flow_browser import (
    FlowManualInterventionRequiredError,
    GoogleFlowImageProvider,
    GoogleFlowVideoProvider,
    check_flow_cdp_status,
)
from app.providers.registry import get_image_provider, get_tts_provider, get_video_provider
from app.storage.project_store import ProjectStore, set_project_store


@pytest.mark.asyncio
async def test_flow_cdp_status_and_provider_routing() -> None:
    """Verify `flow_browser` provider registration and graceful offline CDP diagnostic."""
    cfg = ProviderSettings(
        image_vendor="flow_browser",
        video_vendor="flow_browser",
        tts_vendor="edge_tts",
        flow_cdp_url="http://127.0.0.1:19999",
    )
    img_p = get_image_provider(cfg)
    vid_p = get_video_provider(cfg)
    tts_p = get_tts_provider(cfg)

    assert isinstance(img_p, GoogleFlowImageProvider)
    assert isinstance(vid_p, GoogleFlowVideoProvider)
    assert tts_p.vendor_name == "edge_tts"

    # Unreachable local CDP port returns clean structured diagnostic without crashing
    st = await check_flow_cdp_status(cdp_url="http://127.0.0.1:19999")
    assert st["connected"] is False
    assert "launch_local_chrome.py" in st["message"]

    # Attempting generation when Chrome CDP is closed raises FlowManualInterventionRequiredError cleanly
    with pytest.raises(FlowManualInterventionRequiredError):
        await vid_p.generate_video(
            prompt="Vertical 9:16 cinema shot",
            start_image=Path("/tmp/nonexistent.png"),
            output_path=Path("/tmp/out.mp4"),
        )


@pytest.mark.asyncio
async def test_phase2_full_video_soundtrack_upload_and_master_mp4_e2e(tmp_path: Path) -> None:
    """Verify full Phase 1 -> Phase 2 video clip synthesis, manual MP4 upload replacement, and H.264+AAC master muxing."""
    store = ProjectStore(base_dir=tmp_path / "workspaces")
    set_project_store(store)
    update_settings(
        {
            "llm_vendor": "mock",
            "image_vendor": "mock",
            "video_vendor": "mock",
            "tts_vendor": "mock",
        }
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teststudio") as client:
        # 1. Check Flow status & settings endpoints
        flow_resp = await client.get("/api/flow-browser/status?cdp_url=http://127.0.0.1:19998")
        assert flow_resp.status_code == 200
        assert flow_resp.json()["connected"] is False

        # 2. Run Phase 1 in AUTO mode (4 shots for fast E2E verification)
        create_resp = await client.post(
            "/api/projects?background=false",
            json={
                "topic": "暴风雪夜边关古驿站，左耳戴银铃耳坠、背负藏锋竹骨油纸伞的红衣侠女识破掌柜破绽拔剑反击",
                "aspect_ratio": "9:16",
                "target_duration_sec": 12.0,
                "execution_mode": "auto",
                "shot_count_hint": 4,
            },
        )
        assert create_resp.status_code == 200
        p1 = create_resp.json()
        pid = p1["project_id"]
        assert p1["stage"] == WorkflowStage.PHASE1_COMPLETED.value

        # Verify every motion blueprint includes a Google Flow English native prompt
        assert len(p1["motion_blueprints"]) == len(p1["shots"])
        for mb in p1["motion_blueprints"]:
            assert "35mm live-action cinema film" in mb["flow_english_prompt"]
            assert "Native audio:" in mb["flow_english_prompt"]

        # 3. Run Phase 2 full video rendering + 4-stem soundtrack + PyAV master MP4 muxing
        p2_resp = await client.post(f"/api/projects/{pid}/run-phase2?background=false")
        assert p2_resp.status_code == 200
        p2 = p2_resp.json()
        assert p2["stage"] == WorkflowStage.COMPLETED.value
        assert p2["final_video_url"] is not None
        assert p2["soundtrack_url"] is not None

        for shot in p2["shots"]:
            assert shot["video_clip_url"] is not None
            clip_file = store.resolve_asset_url_to_path(shot["video_clip_url"])
            assert clip_file is not None and clip_file.exists() and clip_file.stat().st_size > 5_000

        # Inspect final_master.mp4 streams via PyAV (must have H.264 video @ 720x1280 + stereo AAC audio!)
        master_file = store.final_video_path(pid)
        assert master_file.exists() and master_file.stat().st_size > 25_000

        container = av.open(str(master_file))
        v_streams = list(container.streams.video)
        a_streams = list(container.streams.audio)
        assert len(v_streams) == 1
        assert len(a_streams) == 1
        assert v_streams[0].width == 720
        assert v_streams[0].height == 1280
        assert v_streams[0].codec_context.name == "h264"
        assert a_streams[0].codec_context.name == "aac"
        container.close()

        # 4. Test manual Google Flow `.mp4` clip upload endpoint replacing Shot 1 + auto-recompose
        shot1_clip_bytes = store.resolve_asset_url_to_path(p2["shots"][0]["video_clip_url"]).read_bytes()
        upload_resp = await client.post(
            f"/api/projects/{pid}/shots/1/upload-video?auto_recompose=true",
            files={"file": ("flow_shot_01.mp4", shot1_clip_bytes, "video/mp4")},
        )
        assert upload_resp.status_code == 200
        uploaded_state = upload_resp.json()
        assert "shot_01_uploaded.mp4" in uploaded_state["shots"][0]["video_clip_url"]
        assert uploaded_state["stage"] == WorkflowStage.COMPLETED.value

        # 5. Test downloading final_master.mp4
        dl_resp = await client.get(f"/api/projects/{pid}/final-video")
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "video/mp4"
        assert len(dl_resp.content) > 25_000
