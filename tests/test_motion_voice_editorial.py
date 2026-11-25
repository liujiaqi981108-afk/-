"""Unit tests for 07 MotionDirector, 08 VoiceAndSoundDirector, and 09 MasterEditor."""

from __future__ import annotations

from pathlib import Path
import pytest

from app.agents.director import DirectorOrchestratorAgent
from app.models.schemas import CreateProjectRequest, ExecutionMode, VideoGenMode
from app.storage.project_store import ProjectStore


@pytest.mark.asyncio
async def test_motion_kinematics_voice_foley_and_editorial_manifest(tmp_path: Path) -> None:
    store = ProjectStore(base_dir=tmp_path)
    orch = DirectorOrchestratorAgent(store=store)
    state = await store.create_project(
        CreateProjectRequest(
            topic="暴风雪夜古驿站，左耳戴银铃耳坠、背负油纸伞的红衣侠女拔剑反杀",
            execution_mode=ExecutionMode.AUTO,
        )
    )
    final_state = await orch.run_from_start(state.project_id)

    # 1. Verify 07 MotionDirectorAgent capabilities
    assert len(final_state.motion_blueprints) == len(final_state.shots)
    kf2v_items = [
        m for m in final_state.motion_blueprints if m.generation_mode == VideoGenMode.FIRST_LAST_KEYFRAME_KF2V
    ]
    assert len(kf2v_items) >= 1
    climax_motion = kf2v_items[0]
    assert climax_motion.start_keyframe_ref is not None
    assert climax_motion.end_keyframe_ref is not None
    assert "[Phase A" in climax_motion.temporal_tri_slice_prompt
    assert "[Phase B" in climax_motion.temporal_tri_slice_prompt
    assert "[Phase C" in climax_motion.temporal_tri_slice_prompt
    assert "4-8帧阻尼惯性" in climax_motion.kinematics.secondary_overlapping_motion
    assert "动静互补防糊片铁律" in climax_motion.camera_rig.counterbalance_rule_applied
    assert "橡胶剑弯曲" in climax_motion.rigid_prop_guardrail
    assert 1 <= climax_motion.hyperparams.motion_intensity <= 9

    # 2. Verify 08 VoiceAndSoundDirectorAgent Vocal DNA, Foley & Music Drop
    assert len(final_state.vocal_profiles) >= 2
    assert len(final_state.sound_blueprints) == len(final_state.shots)
    assert any(sb.has_music_drop for sb in final_state.sound_blueprints)
    all_foley_links = {
        fc.linked_prop_or_surface_id
        for sb in final_state.sound_blueprints
        for fc in sb.foley_cues
    }
    assert "prop_chekhov_01" in all_foley_links
    assert "acc_hero_ear_01" in all_foley_links

    # 3. Verify 09 MasterEditorAgent Sweet-Spot Trim, J/L-Cut, Speed Ramp & Safe-Zone Subtitles
    assert len(final_state.editorial_blueprints) == len(final_state.shots)
    assert any(eb.audio_cut_type in ("j_cut_lead_in", "l_cut_trail_out") for eb in final_state.editorial_blueprints)
    assert any("Speed Ramp" in eb.speed_ramp_curve for eb in final_state.editorial_blueprints)
    for eb in final_state.editorial_blueprints:
        assert eb.sweet_spot_in_frame >= 1
        assert eb.sweet_spot_out_frame > eb.sweet_spot_in_frame
        for sub in eb.safe_zone_subtitles:
            assert len(sub) <= 11
