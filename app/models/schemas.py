"""Complete strongly-typed Pydantic v2 data contracts for the 9-Agent Studio."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionMode(str, Enum):
    HITL = "hitl"
    AUTO = "auto"


class AspectRatio(str, Enum):
    VERTICAL_9_16 = "9:16"
    HORIZONTAL_16_9 = "16:9"


class WorkflowStage(str, Enum):
    CREATED = "CREATED"
    PLANNING_SCRIPT = "PLANNING_SCRIPT"
    AWAITING_SCRIPT_APPROVAL = "AWAITING_SCRIPT_APPROVAL"
    BUILDING_ASSETS = "BUILDING_ASSETS"
    AWAITING_ASSET_APPROVAL = "AWAITING_ASSET_APPROVAL"
    GENERATING_STORYBOARD = "GENERATING_STORYBOARD"
    REVIEWING_STORYBOARD = "REVIEWING_STORYBOARD"
    AWAITING_STORYBOARD_APPROVAL = "AWAITING_STORYBOARD_APPROVAL"
    COMPILING_MANIFEST = "COMPILING_MANIFEST"
    PHASE1_COMPLETED = "PHASE1_COMPLETED"
    GENERATING_VIDEOS = "GENERATING_VIDEOS"
    COMPOSITING_FINAL = "COMPOSITING_FINAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ==============================================================================
# Agent 01: DirectorOrchestratorAgent — Aesthetic Charter, Color Script & Ledger
# ==============================================================================


class ActColorNode(BaseModel):
    act_phase: Literal["hook", "setup", "escalation", "climax", "afterglow"]
    kelvin_temp: str
    dominant_and_accent_hex: list[str] = Field(default_factory=list)
    lighting_mood_note: str = ""
    luminance_contrast_ratio: str = "Low-key 6:1"


class ContinuityLedgerEntry(BaseModel):
    shot_id: int
    story_time_progress: str = ""
    character_physical_states: dict[str, str] = Field(default_factory=dict)
    prop_spatial_states: dict[str, str] = Field(default_factory=dict)
    environment_damage_persisted: list[str] = Field(default_factory=list)


class DirectorCharterAndLedger(BaseModel):
    title: str
    visual_medium_lock: str
    style_preset: str
    target_total_duration_sec: float
    aspect_framing_mandate: str
    global_negative_mandate: str
    color_script_arc: list[ActColorNode] = Field(default_factory=list)
    continuity_ledger: list[ContinuityLedgerEntry] = Field(default_factory=list)
    arbitration_logs: list[str] = Field(default_factory=list)
    fallback_rewrites: list[str] = Field(default_factory=list)


# ==============================================================================
# Agent 02: StoryStrategistAgent — High-Concept Dramaturgy, Subtext & Chekhov
# ==============================================================================


class InformationAsymmetryMode(str, Enum):
    OMNISCIENT_SUSPENSE = "omniscient_suspense"
    ANOMALY_MYSTERY = "anomaly_mystery"
    MISDIRECTION_TWIST = "misdirection_twist"


class IcebergCharacterSoul(BaseModel):
    character_id: str
    name: str
    archetype_and_role: str
    outer_mask: str
    hidden_agenda: str
    behavioral_tic: str
    speech_fingerprint: str
    micro_arc_shift: str


class ChekhovPropArc(BaseModel):
    prop_id: str
    prop_name: str
    owner_character_id: str
    plant_beat: str
    escalation_beat: str
    payoff_climax_beat: str


class SubtextLineSpec(BaseModel):
    beat_index: int
    speaker_id: str
    speaker_name: str
    surface_line: str
    subtext_intent: str
    silence_before_ms: int = 350


class StoryStrategyBlueprint(BaseModel):
    story_synopsis: str
    high_concept_irony: str
    single_emotional_currency: str
    asymmetry_mode: InformationAsymmetryMode
    opening_0_8s_hook_design: str
    micro_hook_relay_chain: list[str] = Field(default_factory=list)
    iceberg_characters: list[IcebergCharacterSoul] = Field(default_factory=list)
    chekhov_props: list[ChekhovPropArc] = Field(default_factory=list)
    subtext_dialogue_list: list[SubtextLineSpec] = Field(default_factory=list)
    sensory_synesthesia_points: list[str] = Field(default_factory=list)
    quiet_before_storm_beat: str
    loop_and_easter_egg: str
    anti_cliche_audit_passed: bool = True
    cliche_rewrites_log: list[str] = Field(default_factory=list)


# ==============================================================================
# Agent 04: ArtDirectorAgent — 5D Character 3-Views, Props & 3D Scene Plates
# (Defined before ShotSpec so enums/types can be shared cleanly)
# ==============================================================================


class BodyViewAngle(str, Enum):
    FRONT = "front"
    THREE_QUARTER_FRONT = "3_4_front"
    SIDE_PROFILE = "side_profile"
    THREE_QUARTER_BACK = "3_4_back"
    BACK = "back"


class AccessorySpec(BaseModel):
    accessory_id: str
    name: str
    wear_location: str  # e.g., "left_ear", "right_wrist", "neck_front", "hair_back_crown"
    visible_angles: list[BodyViewAngle] = Field(default_factory=list)
    material_and_detail: str
    is_flexible_pendulum: bool = True


class CarriedPropSpec(BaseModel):
    prop_id: str
    name: str
    is_chekhov_gun: bool = False
    is_rigid_body: bool = True
    scale_reference: str
    visual_detail: str
    carried_state_desc: str
    active_held_state_desc: str


class CharacterAssetCard(BaseModel):
    character_id: str
    name: str
    role_type: str
    anatomy_and_silhouette: str
    hair_front: str
    hair_side: str
    hair_back: str
    wardrobe_layered: str
    signature_colors: list[str] = Field(default_factory=list)
    accessories: list[AccessorySpec] = Field(default_factory=list)
    carried_props: list[CarriedPropSpec] = Field(default_factory=list)
    negative_drift_tokens: list[str] = Field(default_factory=list)
    turnaround_prompt: str = ""
    turnaround_image_url: Optional[str] = None


class SceneAssetCard(BaseModel):
    scene_id: str
    name: str
    compass_topology: dict[str, str] = Field(default_factory=dict)
    foreground_layer: str
    midground_interactive_props: str
    background_world_details: str
    floor_material_and_acoustic: str
    lighting_and_atmosphere: str
    palette_hex: list[str] = Field(default_factory=list)
    master_plate_prompt: str = ""
    master_plate_image_url: Optional[str] = None


class AssetBible(BaseModel):
    global_style_tokens: str
    global_negative_tokens: str
    characters: list[CharacterAssetCard] = Field(default_factory=list)
    scenes: list[SceneAssetCard] = Field(default_factory=list)


# ==============================================================================
# Agent 03, 05 & 06: StoryboardDirector, StoryboardArtist & VisualCritic
# ==============================================================================


class KeyframeStrategy(str, Enum):
    SINGLE_START_FRAME = "single_start_frame"
    FIRST_AND_LAST_FRAMES = "first_and_last_frames"


class DurationBudgetBreakdown(BaseModel):
    visual_read_sec: float
    action_physics_sec: float
    speech_plus_breath_sec: float
    final_duration_sec: float
    total_frames_24fps: int
    i2v_raw_generation_sec: float = 5.0
    trim_in_frame: int = 1
    trim_out_frame: int = 72
    duration_rationale: str


class FrameSnapshotSpec(BaseModel):
    frame_index: int
    timestamp_sec: float
    beat_label: Literal["start_keyframe", "micro_beat", "apex_beat", "end_keyframe"]
    pose_and_expression: str
    prop_and_cloth_state: str
    camera_and_focus_state: str
    sync_sound_cue: str = ""


class ShotSixWOneHMatrix(BaseModel):
    # WHO
    primary_subject_id: str
    co_present_character_ids: list[str] = Field(default_factory=list)
    secondary_and_offscreen_who: str
    character_continuity_state: str
    prop_active_states: dict[str, Literal["carried", "active_held", "dropped_grounded"]] = Field(
        default_factory=dict
    )
    # WHAT
    narrative_beat_goal: str
    physical_action_and_prop_event: str
    environmental_chain_reaction: str
    chekhov_prop_featured: Optional[str] = None
    # WHEN
    story_time_node: str
    timeline_in_sec: float
    timeline_out_sec: float
    temporal_speed_mode: Literal["real_time_1x", "slow_mo_0.5x", "ramped_speed"] = "real_time_1x"
    # WHERE
    scene_id: str
    camera_compass_facing: Literal["north", "east", "south", "west"] = "north"
    spatial_zone_and_ground: str
    # WHICH
    which_shot_size: Literal["ECU", "CU", "MCU", "MS", "MLS", "WS"] = "MS"
    which_lens_and_aperture: str = "50mm f/1.8"
    which_keyframe_strategy: KeyframeStrategy = KeyframeStrategy.SINGLE_START_FRAME
    which_focus_plane_and_shift: str
    which_cut_transition: Literal[
        "cut_on_action", "eyeline_match_cut", "graphic_match", "j_cut_lead", "hard_cut"
    ] = "cut_on_action"
    # WHY
    dramatic_motivation: str
    # HOW
    camera_angle_and_movement: str
    lighting_and_color_contrast: str
    natural_acting_subtext: str
    narration_and_sound_design: str


class SpatialBlockingSpec(BaseModel):
    horizontal_zone: Literal["left_third", "center", "right_third"] = "center"
    depth_plane: Literal["foreground", "midground", "background"] = "midground"
    camera_elevation: Literal["low_angle_15", "eye_level", "high_angle_20"] = "eye_level"
    body_view_angle: BodyViewAngle = BodyViewAngle.THREE_QUARTER_FRONT
    eyeline_direction: str = "screen_right_mid"
    ground_contact_and_shadow: str = ""
    environment_interaction: str = ""


class AntiClippingPoseSpec(BaseModel):
    is_large_action: bool = False
    frozen_moment_phase: Literal["anticipation", "apex", "follow_through", "natural_rest"] = (
        "natural_rest"
    )
    center_of_gravity_support: str = ""
    limb_prop_separation_rule: str = ""
    hand_grip_topology: str = ""
    dynamic_negative_prompts: list[str] = Field(default_factory=list)


class MultiCharacterCoFramingSpec(BaseModel):
    is_multi_character: bool = False
    left_zone_character_id: Optional[str] = None
    right_zone_character_id: Optional[str] = None
    spatial_partitions: list[str] = Field(default_factory=list)
    mutual_eyeline_vector: str = ""
    contact_separation_geometry: str = ""


class PrescriptionTier(str, Enum):
    NONE = "none"
    TIER1_PROMPT_WEIGHT = "tier1_prompt_weight"
    TIER2_CAMERA_EVASION = "tier2_camera_evasion"
    TIER3_CREATIVE_FALLBACK = "tier3_creative_fallback"


class FiveDimQAReport(BaseModel):
    identity_and_props_score: int
    anatomy_and_anticlipping_score: int
    spatial_and_pose_naturalness_score: int
    scene_richness_and_lighting_score: int
    i2v_motion_readiness_score: int
    strip_continuity_passed: bool = True
    tri_image_diff_findings: list[str] = Field(default_factory=list)
    defect_codes_triggered: list[str] = Field(default_factory=list)
    overall_passed: bool
    prescription_tier: PrescriptionTier = PrescriptionTier.NONE
    revision_prescription: str = ""
    attempt_count: int = 1
    history_notes: list[str] = Field(default_factory=list)


class ShotSpec(BaseModel):
    shot_id: int
    beat_phase: Literal["hook", "setup", "escalation", "climax", "afterglow"]
    speaker_id: Optional[str] = None
    narration: str = ""
    subtext_note: str = ""
    is_creative_fallback_montage: bool = False
    duration_budget: DurationBudgetBreakdown
    six_w_one_h: ShotSixWOneHMatrix
    start_frame: FrameSnapshotSpec
    mid_beat_frames: list[FrameSnapshotSpec] = Field(default_factory=list)
    end_frame: FrameSnapshotSpec
    spatial_blocking: SpatialBlockingSpec
    anticlipping_pose: AntiClippingPoseSpec
    co_framing: MultiCharacterCoFramingSpec = Field(default_factory=MultiCharacterCoFramingSpec)
    # T2I Compiled Artifacts
    reference_image_urls: list[str] = Field(default_factory=list)
    view_sliced_identity_tokens: str = ""
    start_keyframe_prompt: str = ""
    start_negative_prompt: str = ""
    start_keyframe_url: Optional[str] = None
    end_keyframe_prompt: str = ""
    end_keyframe_url: Optional[str] = None
    qa_report: Optional[FiveDimQAReport] = None
    # Phase 2 Rendered Clip Artifacts
    video_clip_url: Optional[str] = None
    audio_clip_url: Optional[str] = None


# ==============================================================================
# Agent 07, 08 & 09: MotionDirector, VoiceAndSoundDirector & MasterEditor
# ==============================================================================


class VideoGenMode(str, Enum):
    SINGLE_FRAME_I2V = "single_frame_i2v"
    FIRST_LAST_KEYFRAME_KF2V = "first_last_kf2v"
    SUBJECT_REF_GUARDED_I2V = "subject_ref_i2v"


class ThreeLayerKinematicsSpec(BaseModel):
    primary_skeletal_drive: str
    secondary_overlapping_motion: str
    tertiary_env_and_light_coupling: str


class CameraRigAndParallaxSpec(BaseModel):
    rig_type: Literal[
        "tripod_locked",
        "dolly_track_smooth",
        "steadicam_follow",
        "handheld_subtle_breathing",
        "crane_jib_rise",
    ]
    movement_trajectory: str
    parallax_ratio_desc: str
    rack_focus_plan: str
    counterbalance_rule_applied: str


class MotionHyperparameters(BaseModel):
    motion_intensity: int = Field(ge=1, le=10)
    subject_fidelity_weight: float = Field(ge=0.5, le=0.98)
    shutter_angle_deg: int = 180
    recommended_raw_sec: float = 5.0


class ShotMotionBlueprint(BaseModel):
    shot_id: int
    generation_mode: VideoGenMode
    start_keyframe_ref: Optional[str] = None
    end_keyframe_ref: Optional[str] = None
    subject_turnaround_refs: list[str] = Field(default_factory=list)
    temporal_tri_slice_prompt: str
    flow_english_prompt: str = ""
    kinematics: ThreeLayerKinematicsSpec
    camera_rig: CameraRigAndParallaxSpec
    rigid_prop_guardrail: str
    dynamic_negative_prompt: str
    hyperparams: MotionHyperparameters


class CharacterVocalProfile(BaseModel):
    character_id: str
    character_name: str
    voice_anchor_id: str
    resonance_and_timbre: str
    pitch_and_tempo_baseline: str
    cadence_habit: str
    reference_prompt_spec: str


class FoleyFrameCue(BaseModel):
    frame_index: int
    timestamp_sec: float
    linked_prop_or_surface_id: str
    source_material: str
    sound_description: str
    stereo_pan: Literal["L", "C", "R", "L->R", "R->L"] = "C"


class ShotSoundBlueprint(BaseModel):
    shot_id: int
    speaker_id: Optional[str] = None
    voice_anchor_id: Optional[str] = None
    lip_sync_mode: Literal[
        "on_camera_short_sync", "off_camera_reaction", "inner_monologue_vo", "breath_foley_only"
    ]
    spatial_reverb_preset: Literal[
        "close_dry_vo", "wooden_hall_reverb", "snow_outdoor_open", "stone_alley_echo", "off_axis_muffled"
    ]
    physiological_acting_script: str
    foley_cues: list[FoleyFrameCue] = Field(default_factory=list)
    continuous_room_tone: str
    score_and_music_drop: str
    has_music_drop: bool = False


class ShotEditorialBlueprint(BaseModel):
    shot_id: int
    sweet_spot_in_frame: int
    sweet_spot_out_frame: int
    effective_trimmed_sec: float
    cut_on_action_phase: str
    eye_trace_screen_zone: str
    audio_cut_type: Literal["straight_cut", "j_cut_lead_in", "l_cut_trail_out"]
    audio_offset_sec: float = 0.0
    speed_ramp_curve: str
    color_match_and_grain: str
    ducking_and_loudness: str
    safe_zone_subtitles: list[str] = Field(default_factory=list)


class StripContinuityReport(BaseModel):
    passed: bool = True
    checked_pairs: int = 0
    axis_and_eyeline_notes: list[str] = Field(default_factory=list)
    prop_continuity_notes: list[str] = Field(default_factory=list)


class Phase2ProductionManifest(BaseModel):
    project_id: str
    generated_at: str = Field(default_factory=utc_now_iso)
    aspect_ratio: AspectRatio
    total_duration_sec: float
    total_shots: int
    visual_medium_lock: str
    vocal_profiles: list[CharacterVocalProfile] = Field(default_factory=list)
    motion_blueprints: list[ShotMotionBlueprint] = Field(default_factory=list)
    sound_blueprints: list[ShotSoundBlueprint] = Field(default_factory=list)
    editorial_blueprints: list[ShotEditorialBlueprint] = Field(default_factory=list)


# ==============================================================================
# Project Container & Live SSE Event Models
# ==============================================================================


class CreateProjectRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=1500)
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL_9_16
    target_duration_sec: float = Field(default=16.0, ge=8.0, le=60.0)
    style_preset: str = "35mm 冷峻电影胶片写实"
    execution_mode: ExecutionMode = ExecutionMode.HITL
    shot_count_hint: Optional[int] = Field(default=None, ge=3, le=12)


class AgentActivityEvent(BaseModel):
    event_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
    agent_id: str
    agent_name: str
    phase: str
    level: Literal["info", "success", "warn", "prescription", "gate"] = "info"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ProjectState(BaseModel):
    project_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    topic: str
    aspect_ratio: AspectRatio = AspectRatio.VERTICAL_9_16
    target_duration_sec: float = 16.0
    style_preset: str = "35mm 冷峻电影胶片写实"
    execution_mode: ExecutionMode = ExecutionMode.HITL
    shot_count_hint: Optional[int] = None

    stage: WorkflowStage = WorkflowStage.CREATED
    active_agent: Optional[str] = None
    error_message: Optional[str] = None

    director_charter: Optional[DirectorCharterAndLedger] = None
    story_strategy: Optional[StoryStrategyBlueprint] = None
    shots: list[ShotSpec] = Field(default_factory=list)
    asset_bible: Optional[AssetBible] = None
    vocal_profiles: list[CharacterVocalProfile] = Field(default_factory=list)
    strip_audit: Optional[StripContinuityReport] = None
    motion_blueprints: list[ShotMotionBlueprint] = Field(default_factory=list)
    sound_blueprints: list[ShotSoundBlueprint] = Field(default_factory=list)
    editorial_blueprints: list[ShotEditorialBlueprint] = Field(default_factory=list)
    manifest_url: Optional[str] = None
    soundtrack_url: Optional[str] = None
    final_video_url: Optional[str] = None

    agent_logs: list[AgentActivityEvent] = Field(default_factory=list)
