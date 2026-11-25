"""Unit tests for 04 ArtDirector, 05 StoryboardArtist, and 06 VisualCritic."""

from __future__ import annotations

from pathlib import Path
from PIL import Image
import pytest

from app.agents.director import DirectorOrchestratorAgent
from app.agents.storyboard_artist import StoryboardArtistAgent
from app.models.schemas import (
    AspectRatio,
    BodyViewAngle,
    CreateProjectRequest,
    ExecutionMode,
    KeyframeStrategy,
)
from app.storage.project_store import ProjectStore


@pytest.mark.asyncio
async def test_turnaround_3view_view_slicing_coframing_and_qa_self_heal(tmp_path: Path) -> None:
    store = ProjectStore(base_dir=tmp_path)
    orch = DirectorOrchestratorAgent(store=store)
    state = await store.create_project(
        CreateProjectRequest(
            topic="暴风雪夜古驿站，左耳戴银铃耳坠、背负油纸伞的红衣侠女与掌柜对峙后拔出伞中细剑",
            aspect_ratio=AspectRatio.VERTICAL_9_16,
            execution_mode=ExecutionMode.HITL,
        )
    )
    state = await orch.run_stage1_script(state.project_id)
    state = await orch.run_stage2_assets(state.project_id)

    assert state.asset_bible is not None
    hero = state.asset_bible.characters[0]

    # 1. Verify 1440x960 Character 3-View Turnaround Sheet & Chekhov Prop Dual-State
    turnaround_path = store.resolve_asset_url_to_path(hero.turnaround_image_url)
    assert turnaround_path is not None and turnaround_path.exists()
    with Image.open(turnaround_path) as im:
        assert im.size == (1440, 960)

    assert hero.hair_front and hero.hair_side and hero.hair_back
    assert any(p.prop_id == "prop_chekhov_01" and p.is_chekhov_gun for p in hero.carried_props)

    # 2. Verify View-Aware Anchor Slicing on 180° BACK view vs FRONT view
    back_tokens = StoryboardArtistAgent.slice_character_anchors_by_view(
        hero, BodyViewAngle.BACK, "CU", {"prop_chekhov_01": "carried"}
    )
    assert hero.hair_back in back_tokens
    assert "严禁出现正脸五官" in back_tokens
    # Left-ear front accessory must NOT be injected as visible in 180° back view!
    assert hero.accessories[0].name not in back_tokens

    front_active_tokens = StoryboardArtistAgent.slice_character_anchors_by_view(
        hero, BodyViewAngle.FRONT, "MS", {"prop_chekhov_01": "active_held"}
    )
    assert hero.accessories[0].name in front_active_tokens
    assert "手持激活态" in front_active_tokens

    # 3. Run Stage 3 Storyboard + 5D Visual Critic QA + Pairwise Strip Audit
    state = await orch.run_stage3_storyboard_and_qa(state.project_id)

    # Shot 2 is multi-character co-framing: verify Left/Right Partition Isolation!
    co_shot = next(s for s in state.shots if len(s.six_w_one_h.co_present_character_ids) >= 2)
    assert co_shot.co_framing.is_multi_character is True
    assert len(co_shot.co_framing.spatial_partitions) == 2
    assert "LEFT SCREEN PARTITION" in co_shot.start_keyframe_prompt
    assert "RIGHT SCREEN PARTITION" in co_shot.start_keyframe_prompt

    # Shot 5 is large-action climax: verify Dual Keyframes (Start + End) & Tier-2 QA Self-Heal!
    climax_shot = next(
        s for s in state.shots if s.six_w_one_h.which_keyframe_strategy == KeyframeStrategy.FIRST_AND_LAST_FRAMES
    )
    assert climax_shot.start_keyframe_url is not None
    assert climax_shot.end_keyframe_url is not None
    assert climax_shot.qa_report is not None
    assert climax_shot.qa_report.overall_passed is True
    assert climax_shot.qa_report.attempt_count == 2
    assert any("tier2_camera_evasion" in h for h in climax_shot.qa_report.history_notes)

    # Verify Pairwise Strip Continuity Audit passed across all cuts
    assert state.strip_audit is not None
    assert state.strip_audit.passed is True
    assert state.strip_audit.checked_pairs == len(state.shots) - 1


@pytest.mark.asyncio
async def test_tier3_creative_fallback_montage_circuit_breaker(tmp_path: Path) -> None:
    store = ProjectStore(base_dir=tmp_path)
    orch = DirectorOrchestratorAgent(store=store)
    state = await store.create_project(CreateProjectRequest(topic="风雪古驿高难拼刀熔断测试"))
    state = await orch.run_stage1_script(state.project_id)
    state = await orch.run_stage2_assets(state.project_id)

    assert state.asset_bible and state.director_charter
    target_shot = state.shots[4]
    healed_shot = await orch._render_and_inspect_single_shot(
        project_id=state.project_id,
        shot=target_shot,
        aspect_ratio=state.aspect_ratio,
        bible=state.asset_bible,
        charter=state.director_charter,
        extra_qa_ctx={"force_fail_tier": "tier3"},
    )
    assert healed_shot.is_creative_fallback_montage is True
    assert healed_shot.qa_report is not None and healed_shot.qa_report.overall_passed is True
    assert len(state.director_charter.fallback_rewrites) >= 1
