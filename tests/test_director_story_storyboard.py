"""Unit tests for 01 DirectorOrchestrator, 02 StoryStrategist, and 03 StoryboardDirector."""

from __future__ import annotations

from pathlib import Path
import pytest

from app.agents.director import DirectorOrchestratorAgent
from app.agents.story_strategist import StoryStrategistAgent
from app.agents.storyboard_director import StoryboardDirectorAgent
from app.models.schemas import (
    AspectRatio,
    CreateProjectRequest,
    ExecutionMode,
    KeyframeStrategy,
    SubtextLineSpec,
)
from app.storage.project_store import ProjectStore


@pytest.mark.asyncio
async def test_story_anti_cliche_auditor_and_chekhov_binding(tmp_path: Path) -> None:
    store = ProjectStore(base_dir=tmp_path)
    orch = DirectorOrchestratorAgent(store=store)
    state = await store.create_project(
        CreateProjectRequest(
            topic="暴风雪夜边关古驿站，红衣侠女借油纸伞暗剑破局",
            aspect_ratio=AspectRatio.VERTICAL_9_16,
            execution_mode=ExecutionMode.HITL,
        )
    )
    charter = await orch.build_charter(state)

    # Verify 01 Director Charter & 5-Act Color Script & Safe-Zone Mandate
    assert len(charter.color_script_arc) == 5
    assert "底部 20% 字幕净空区" in charter.aspect_framing_mandate

    # Verify AntiClicheAuditor catches blacklisted AI clichés & >11-char verbose lines
    bad_lines = [
        SubtextLineSpec(
            beat_index=1,
            speaker_id="char_hero",
            speaker_name="沈惊鸿",
            surface_line="命运的齿轮开始转动，今天就是你的死期！",
            subtext_intent="直白网文废话测试",
        ),
        SubtextLineSpec(
            beat_index=2,
            speaker_id="char_rival",
            speaker_name="陆掌柜",
            surface_line="姑娘你觉得今天晚上这场暴风雪会不会把整座山都彻底封住呢？",
            subtext_intent="超长啰嗦句子测试",
        ),
    ]
    purified, rewrites, passed = StoryStrategistAgent.audit_and_purify_subtext(bad_lines)
    assert passed is True
    assert len(rewrites) == 2
    for ln in purified:
        assert "命运的齿轮" not in ln.surface_line
        core_chars = [c for c in ln.surface_line if c not in "，。？！…—、,.?! "]
        assert len(core_chars) <= 11

    # Verify full 02 StoryStrategyBlueprint
    strategy = await orch.story_strategist.build_story_strategy(state.project_id, state.topic, charter)
    assert strategy.anti_cliche_audit_passed is True
    assert len(strategy.micro_hook_relay_chain) >= 3
    assert len(strategy.iceberg_characters) >= 2
    assert strategy.iceberg_characters[0].outer_mask != strategy.iceberg_characters[0].hidden_agenda
    assert len(strategy.chekhov_props) >= 1
    assert strategy.chekhov_props[0].prop_id == "prop_chekhov_01"


@pytest.mark.asyncio
async def test_scientific_duration_formula_action_split_and_24fps_frames(tmp_path: Path) -> None:
    store = ProjectStore(base_dir=tmp_path)
    orch = DirectorOrchestratorAgent(store=store)
    state = await store.create_project(
        CreateProjectRequest(topic="风雪古驿伞剑反杀", target_duration_sec=16.0)
    )
    charter = await orch.build_charter(state)
    strategy = await orch.story_strategist.build_story_strategy(state.project_id, state.topic, charter)
    shots = await orch.storyboard_director.build_storyboard(state.project_id, state.topic, charter, strategy)

    # Non-uniform heartbeat pacing check (not all equal durations!)
    durations = [s.duration_budget.final_duration_sec for s in shots]
    assert len(set(durations)) >= 3

    # Verify 4-constraint envelope formula & 24fps frame math & contiguous timeline
    prev_out = 0.0
    has_dual = False
    for s in shots:
        b = s.duration_budget
        expected_raw = max(b.visual_read_sec, b.action_physics_sec, b.speech_plus_breath_sec)
        expected_clamped = round(min(5.0, max(1.0, expected_raw)), 1)
        assert b.final_duration_sec == pytest.approx(expected_clamped, abs=0.11)
        assert b.total_frames_24fps == round(b.final_duration_sec * 24)
        assert s.six_w_one_h.timeline_in_sec == pytest.approx(prev_out, abs=0.05)
        prev_out = s.six_w_one_h.timeline_out_sec

        # Verify 24fps Start / Mid / End frame blueprint completeness
        assert s.start_frame.frame_index == 1
        assert len(s.mid_beat_frames) >= 1
        assert s.end_frame.frame_index == b.total_frames_24fps
        if s.six_w_one_h.which_keyframe_strategy == KeyframeStrategy.FIRST_AND_LAST_FRAMES:
            has_dual = True
    assert has_dual is True

    # Verify >5.0s overlong action automatic montage split
    overlong_drafts = [{"action_physics_sec": 6.6, "shot_size": "MS", "narration": "测试"}]
    split_res, split_logs = StoryboardDirectorAgent.split_overlong_action_drafts(overlong_drafts)
    assert len(split_res) == 2
    assert len(split_logs) == 1
    assert all(d["action_physics_sec"] <= 5.0 for d in split_res)


@pytest.mark.asyncio
async def test_director_conflict_arbitrator_and_continuity_ledger(tmp_path: Path) -> None:
    store = ProjectStore(base_dir=tmp_path)
    orch = DirectorOrchestratorAgent(store=store)
    state = await store.create_project(CreateProjectRequest(topic="风雪古驿伞剑反杀"))
    charter = await orch.build_charter(state)
    strategy = await orch.story_strategist.build_story_strategy(state.project_id, state.topic, charter)
    shots = await orch.storyboard_director.build_storyboard(state.project_id, state.topic, charter, strategy)

    # Force a speech vs fast-cut conflict on Shot 2 (1.2s cut with a 10-char line needing ~3.5s)
    shots[1].duration_budget.final_duration_sec = 1.2
    shots[1].narration = "风雪封山，姑娘快喝口热汤。"
    shots = orch.arbitrate_script_and_timing(charter, shots, strategy)
    assert shots[1].duration_budget.final_duration_sec > 1.2
    assert any("跨部门冲突裁决" in log for log in charter.arbitration_logs)

    ledger = orch.build_continuity_ledger(charter, shots, strategy)
    assert len(ledger) == len(shots)
    # After climax, environment damage must persist into afterglow shot!
    assert len(ledger[-1].environment_damage_persisted) >= 2
