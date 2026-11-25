"""End-to-End FastAPI integration tests covering Auto mode and 3-Gate HITL with surgical rerolls."""

from __future__ import annotations

from pathlib import Path
import httpx
import pytest

from app.main import create_app
from app.models.schemas import WorkflowStage
from app.storage.project_store import ProjectStore, set_project_store


@pytest.mark.asyncio
async def test_e2e_hitl_three_gates_and_surgical_rerolls(tmp_path: Path) -> None:
    store = ProjectStore(base_dir=tmp_path)
    set_project_store(store)
    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teststudio") as client:
        # Health check verifies 9-Agent roster
        health = await client.get("/api/health")
        assert health.status_code == 200
        assert len(health.json()["agents"]) == 9

        # 1. Create project in HITL mode -> stops at Gate 1 (AWAITING_SCRIPT_APPROVAL)
        r_create = await client.post(
            "/api/projects?background=false",
            json={
                "topic": "赛博朋克霓虹雨夜地下修械铺，戴钛银耳夹与改装怀表的机械少女识破陷阱反杀",
                "aspect_ratio": "9:16",
                "target_duration_sec": 15.0,
                "execution_mode": "hitl",
            },
        )
        assert r_create.status_code == 200
        proj = r_create.json()
        pid = proj["project_id"]
        assert proj["stage"] == WorkflowStage.AWAITING_SCRIPT_APPROVAL.value

        # Test inline script edit on Shot 2 at Gate 1
        r_patch = await client.patch(
            f"/api/projects/{pid}/shots/2",
            json={"narration": "铁叔，你的扳手锈了。", "duration_sec": 3.1},
        )
        assert r_patch.status_code == 200
        assert r_patch.json()["shots"][1]["narration"] == "铁叔，你的扳手锈了。"

        # 2. Approve Gate 1 -> stops at Gate 2 (AWAITING_ASSET_APPROVAL)
        r_g1 = await client.post(f"/api/projects/{pid}/approve-script?background=false")
        assert r_g1.status_code == 200
        assert r_g1.json()["stage"] == WorkflowStage.AWAITING_ASSET_APPROVAL.value

        # Test surgical reroll of single character 1440x960 turnaround at Gate 2
        old_turnaround_url = r_g1.json()["asset_bible"]["characters"][0]["turnaround_image_url"]
        r_char = await client.post(
            f"/api/projects/{pid}/characters/char_hero/reroll",
            json={"custom_note": "强化护目镜黄铜铆钉磨损细节"},
        )
        assert r_char.status_code == 200
        new_turnaround_url = r_char.json()["asset_bible"]["characters"][0]["turnaround_image_url"]
        assert new_turnaround_url != old_turnaround_url

        # 3. Approve Gate 2 -> stops at Gate 3 (AWAITING_STORYBOARD_APPROVAL)
        r_g2 = await client.post(f"/api/projects/{pid}/approve-assets?background=false")
        assert r_g2.status_code == 200
        assert r_g2.json()["stage"] == WorkflowStage.AWAITING_STORYBOARD_APPROVAL.value
        assert all(s["start_keyframe_url"] is not None for s in r_g2.json()["shots"])

        # Test surgical reroll of single shot keyframe at Gate 3 while keeping other shots intact
        shot1_url_before = r_g2.json()["shots"][0]["start_keyframe_url"]
        shot3_url_before = r_g2.json()["shots"][2]["start_keyframe_url"]
        r_shot = await client.post(
            f"/api/projects/{pid}/shots/3/reroll",
            json={"feedback": "增强东窗轮廓暖金背光对比"},
        )
        assert r_shot.status_code == 200
        assert r_shot.json()["shots"][0]["start_keyframe_url"] == shot1_url_before
        assert r_shot.json()["shots"][2]["start_keyframe_url"] != shot3_url_before

        # 4. Approve Gate 3 -> compiles Phase 2 Manifest & reaches PHASE1_COMPLETED
        r_g3 = await client.post(f"/api/projects/{pid}/approve-storyboard?background=false")
        assert r_g3.status_code == 200
        done_state = r_g3.json()
        assert done_state["stage"] == WorkflowStage.PHASE1_COMPLETED.value
        assert done_state["manifest_url"] is not None

        # Verify manifest download endpoint
        r_man = await client.get(f"/api/projects/{pid}/manifest")
        assert r_man.status_code == 200
        manifest_json = r_man.json()
        assert manifest_json["project_id"] == pid
        assert len(manifest_json["motion_blueprints"]) == len(done_state["shots"])
        assert len(manifest_json["sound_blueprints"]) == len(done_state["shots"])
        assert len(manifest_json["editorial_blueprints"]) == len(done_state["shots"])
