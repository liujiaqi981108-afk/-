"""Agent 05: Spatial Blocking, Multi-Character Anti-Bleeding & Anti-Clipping T2I Artist."""

from __future__ import annotations

import time
from typing import Optional

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    AspectRatio,
    AssetBible,
    BodyViewAngle,
    CharacterAssetCard,
    ContinuityLedgerEntry,
    DirectorCharterAndLedger,
    FrameSnapshotSpec,
    KeyframeStrategy,
    MultiCharacterCoFramingSpec,
    SceneAssetCard,
    ShotSpec,
)
from app.providers.base import ImageGenRequest, ReferenceImage


class StoryboardArtistAgent(BaseStudioAgent):
    """05 空间调度与防穿模文生图师：视角锚点裁剪、双人分仓防串色、透视接地阴影、极值防穿模与单/双关键帧生图."""

    agent_id = "agent_05_t2i"
    agent_name = "05 空间调度与防穿模生图师"

    @staticmethod
    def slice_character_anchors_by_view(
        char: CharacterAssetCard,
        view_angle: BodyViewAngle,
        shot_size: str,
        prop_states: dict[str, str],
        ledger_state: str = "",
    ) -> str:
        """Filter character hair, facial marks, left/right accessories, and prop state strictly by camera angle."""
        is_back = view_angle in (BodyViewAngle.BACK, BodyViewAngle.THREE_QUARTER_BACK)
        is_side = view_angle == BodyViewAngle.SIDE_PROFILE
        is_closeup = shot_size in ("ECU", "CU")

        if is_back:
            # CRITICAL: Never inject front facial features (mole/eyes) or front chest pendants on back views!
            hair_clause = f"[背面发型拓扑] {char.hair_back}"
            face_clause = "180°背对镜头，仅展现后脑束发与后颈背影轮廓，严禁出现正脸五官或反向扭头"
        elif is_side:
            hair_clause = f"[90°正侧面发型拓扑] {char.hair_side}"
            face_clause = f"侧面骨相剪影：{char.anatomy_and_silhouette}"
        else:
            hair_clause = f"[正面/前侧发型拓扑] {char.hair_front}"
            # Mirror calibration: character's left ear is on viewer's right side of head!
            face_clause = (
                f"正面骨相：{char.anatomy_and_silhouette}（画面镜像校准：角色左脸特征与左耳配饰位于观者视线右侧）"
            )

        visible_accs = [
            f"{a.name}[部位={a.wear_location}: {a.material_and_detail}]"
            for a in char.accessories
            if not a.visible_angles or view_angle in a.visible_angles
        ]
        acc_clause = "；".join(visible_accs) if visible_accs else "当前背角正面耳饰被头部自然遮挡不可见"

        wardrobe_clause = char.wardrobe_layered
        if is_closeup:
            # Trim boot/lower hem details on close-ups to concentrate token weight on upper frame
            wardrobe_clause = wardrobe_clause.split("【下装与鞋靴】")[0]

        prop_clauses: list[str] = []
        for p in char.carried_props:
            state_mode = prop_states.get(p.prop_id, "carried")
            if state_mode == "active_held":
                prop_clauses.append(f"【手持激活态·{p.name}({p.scale_reference})】{p.active_held_state_desc}")
            elif state_mode == "dropped_grounded":
                prop_clauses.append(f"【脱手落地态·{p.name}】空鞘落于左脚侧0.5米地面透视面上，保持原有比例尺")
            else:
                prop_clauses.append(f"【常驻挂载态·{p.name}({p.scale_reference})】{p.carried_state_desc}")

        cont_clause = f" | 连续性状态继承：{ledger_state}" if ledger_state else ""
        return (
            f"角色[{char.name}] 识别三色锁{char.signature_colors} | {face_clause} | {hair_clause} | "
            f"穿搭：{wardrobe_clause} | 当前视角可见配饰：{acc_clause} | "
            f"随身道具：{'；'.join(prop_clauses)}{cont_clause}"
        )

    @classmethod
    def compile_multi_character_co_framing(
        cls,
        shot: ShotSpec,
        char_map: dict[str, CharacterAssetCard],
    ) -> MultiCharacterCoFramingSpec:
        co_ids = [cid for cid in shot.six_w_one_h.co_present_character_ids if cid in char_map]
        if len(co_ids) < 2:
            return MultiCharacterCoFramingSpec(is_multi_character=False)

        left_char = char_map[co_ids[0]]
        right_char = char_map[co_ids[1]]
        left_slice = cls.slice_character_anchors_by_view(
            left_char,
            BodyViewAngle.SIDE_PROFILE,
            shot.six_w_one_h.which_shot_size,
            shot.six_w_one_h.prop_active_states,
        )
        right_slice = cls.slice_character_anchors_by_view(
            right_char,
            shot.spatial_blocking.body_view_angle,
            shot.six_w_one_h.which_shot_size,
            shot.six_w_one_h.prop_active_states,
        )

        partitions = [
            f"[LEFT SCREEN PARTITION (0%-44% width) - {left_char.name} ONLY, STRICT ATTRIBUTE ISOLATION]: {left_slice}",
            f"[RIGHT SCREEN PARTITION (56%-100% width) - {right_char.name} ONLY, STRICT ATTRIBUTE ISOLATION]: {right_slice}",
        ]
        return MultiCharacterCoFramingSpec(
            is_multi_character=True,
            left_zone_character_id=left_char.character_id,
            right_zone_character_id=right_char.character_id,
            spatial_partitions=partitions,
            mutual_eyeline_vector=(
                f"双向视线几何锁定：左侧{left_char.name}视线沿水平偏下5°投向右侧{right_char.name}手部与腰际，"
                f"右侧{right_char.name}视线精准回锁左侧柜台下方靴尖，严禁对视看空或斗鸡眼"
            ),
            contact_separation_geometry=(
                "双人交互隔离带：画面中央44%-56%保留榆木柜台与热汤白雾作为物理缓冲带，"
                "双方手掌间距保持 >=35cm 清晰空间分离，严禁手部粘连或服饰颜色互相串染(Zero Attribute Bleeding)"
            ),
        )

    @staticmethod
    def enrich_anticlipping_pose(shot: ShotSpec) -> None:
        pose = shot.anticlipping_pose
        base_neg = [
            "extra arms",
            "extra legs",
            "six fingers",
            "fused fingers on weapon hilt",
            "floating feet without ground contact shadow",
            "back view with front face",
        ]
        if pose.is_large_action:
            pose.dynamic_negative_prompts = base_neg + [
                "sword blade clipping through body or arm",
                "cape intersecting torso",
                "bent rubber sword",
                "motion ghosting multiple blades",
                "severed or detached wrist",
            ]
        elif shot.co_framing.is_multi_character:
            pose.dynamic_negative_prompts = base_neg + [
                "attribute bleeding between two characters",
                "swapped outfit colors",
                "two characters wearing identical earrings",
                "merged hands holding bowl",
            ]
        else:
            pose.dynamic_negative_prompts = base_neg

    def _assemble_frame_prompt(
        self,
        shot: ShotSpec,
        frame_spec: FrameSnapshotSpec,
        frame_role_label: str,
        scene: SceneAssetCard,
        charter: DirectorCharterAndLedger,
        act_kelvin_note: str,
        ledger_entry: Optional[ContinuityLedgerEntry],
        revision_prescription: str = "",
    ) -> str:
        compass_dir = shot.six_w_one_h.camera_compass_facing
        wall_anchor = scene.compass_topology.get(compass_dir, "")
        env_damage = (
            f"；保留前镜场景交互痕迹：{', '.join(ledger_entry.environment_damage_persisted)}"
            if ledger_entry and ledger_entry.environment_damage_persisted
            else ""
        )

        subject_block = (
            " || ".join(shot.co_framing.spatial_partitions)
            + f" || {shot.co_framing.mutual_eyeline_vector} || {shot.co_framing.contact_separation_geometry}"
            if shot.co_framing.is_multi_character
            else shot.view_sliced_identity_tokens
        )

        prescription_clause = (
            f"\n[SUPERVISOR SURGICAL FIX MANDATE]: {revision_prescription}"
            if revision_prescription
            else ""
        )

        return (
            f"[{frame_role_label} SINGLE FROZEN INSTANT — DO NOT BLEND MULTIPLE TIMESTEPS]\n"
            f"1. Visual Medium & Lens: {charter.visual_medium_lock} | {shot.six_w_one_h.which_shot_size} shot, "
            f"{shot.six_w_one_h.which_lens_and_aperture}, elevation={shot.spatial_blocking.camera_elevation}. "
            f"Focus: {shot.six_w_one_h.which_focus_plane_and_shift}.\n"
            f"2. Aspect & Safe-Zone Mandate: {charter.aspect_framing_mandate}\n"
            f"3. Color Script & Lighting: {act_kelvin_note} | {scene.lighting_and_atmosphere}.\n"
            f"4. 3D Scene Compass Lock (Camera Facing {compass_dir.upper()}): Background={wall_anchor}; "
            f"Foreground={scene.foreground_layer}; Midground={scene.midground_interactive_props}{env_damage}.\n"
            f"5. Subject Identity & Partition Lock: {subject_block}\n"
            f"6. Exact Frame Pose ({frame_spec.beat_label} @ Frame {frame_spec.frame_index}): "
            f"{frame_spec.pose_and_expression}. {shot.anticlipping_pose.center_of_gravity_support}. "
            f"{shot.anticlipping_pose.limb_prop_separation_rule}. Grip: {shot.anticlipping_pose.hand_grip_topology}.\n"
            f"7. Perspective Grounding & Contact Shadow: Horizontal={shot.spatial_blocking.horizontal_zone}, "
            f"Depth={shot.spatial_blocking.depth_plane}. {shot.spatial_blocking.ground_contact_and_shadow}."
            f"{prescription_clause}"
        )

    async def generate_shot_keyframes(
        self,
        project_id: str,
        shot: ShotSpec,
        aspect_ratio: AspectRatio,
        bible: AssetBible,
        charter: DirectorCharterAndLedger,
        ledger_entry: Optional[ContinuityLedgerEntry] = None,
        revision_prescription: str = "",
    ) -> ShotSpec:
        char_map = {c.character_id: c for c in bible.characters}
        scene_map = {s.scene_id: s for s in bible.scenes}
        primary_char = char_map.get(shot.six_w_one_h.primary_subject_id, bible.characters[0])
        scene = scene_map.get(shot.six_w_one_h.scene_id, bible.scenes[0])

        # 1. Continuity state from 01 Director's Master Ledger
        ledger_char_state = ""
        prop_state_override = dict(shot.six_w_one_h.prop_active_states)
        if ledger_entry:
            ledger_char_state = ledger_entry.character_physical_states.get(primary_char.character_id, "")
            for pid, pval in ledger_entry.prop_spatial_states.items():
                if "落地" in pval or "dropped" in pval:
                    prop_state_override[pid] = "dropped_grounded"  # type: ignore[assignment]

        # 2. View-Aware Anchor Slicing + Multi-Character Co-Framing + Anti-Clipping Pose
        shot.view_sliced_identity_tokens = self.slice_character_anchors_by_view(
            primary_char,
            shot.spatial_blocking.body_view_angle,
            shot.six_w_one_h.which_shot_size,
            prop_state_override,
            ledger_state=ledger_char_state,
        )
        shot.co_framing = self.compile_multi_character_co_framing(shot, char_map)
        self.enrich_anticlipping_pose(shot)

        # 3. Collect Multi-Reference Conditioning Anchors (Character Turnarounds + Scene Master Plate)
        refs: list[ReferenceImage] = []
        ref_urls: list[str] = []
        for cid in shot.six_w_one_h.co_present_character_ids:
            c_obj = char_map.get(cid)
            if c_obj and c_obj.turnaround_image_url:
                c_path = self.store.resolve_asset_url_to_path(c_obj.turnaround_image_url)
                if c_path:
                    refs.append(
                        ReferenceImage(
                            role="character_turnaround",
                            path=c_path,
                            label=f"{c_obj.name}_正侧背三视图",
                            weight=0.88,
                        )
                    )
                    ref_urls.append(c_obj.turnaround_image_url)

        if scene.master_plate_image_url:
            s_path = self.store.resolve_asset_url_to_path(scene.master_plate_image_url)
            if s_path:
                refs.append(
                    ReferenceImage(
                        role="scene_master_plate",
                        path=s_path,
                        label=f"{scene.name}_空镜母版",
                        weight=0.76,
                    )
                )
                ref_urls.append(scene.master_plate_image_url)
        shot.reference_image_urls = ref_urls

        # 4. Match 01 Director's Color Script Node for this shot's act phase
        act_node = next(
            (n for n in charter.color_script_arc if n.act_phase == shot.beat_phase),
            None,
        )
        act_kelvin_note = (
            f"色温={act_node.kelvin_temp}, 反差={act_node.luminance_contrast_ratio}, 主辅色={act_node.dominant_and_accent_hex}"
            if act_node
            else "6500K/3200K 冷暖高反差电影光"
        )
        act_colors = act_node.dominant_and_accent_hex if act_node and act_node.dominant_and_accent_hex else scene.palette_hex

        shot.start_keyframe_prompt = self._assemble_frame_prompt(
            shot=shot,
            frame_spec=shot.start_frame,
            frame_role_label="START KEYFRAME (FRAME 01)",
            scene=scene,
            charter=charter,
            act_kelvin_note=act_kelvin_note,
            ledger_entry=ledger_entry,
            revision_prescription=revision_prescription,
        )
        neg_all = (
            primary_char.negative_drift_tokens
            + shot.anticlipping_pose.dynamic_negative_prompts
            + [bible.global_negative_tokens]
        )
        shot.start_negative_prompt = ", ".join(dict.fromkeys(neg_all))

        w, h = (720, 1280) if aspect_ratio == AspectRatio.VERTICAL_9_16 else (1280, 720)
        pdir = self.store.project_dir(project_id) / "keyframes"
        ts = int(time.time() * 1000)

        rival_char = next((c for c in bible.characters if c.character_id != primary_char.character_id), primary_char)
        any_prop_active = any(v == "active_held" for v in prop_state_override.values())

        start_file = pdir / f"shot_{shot.shot_id:02d}_start.png"
        await self.img.generate_image(
            ImageGenRequest(
                kind="storyboard_keyframe",
                prompt=shot.start_keyframe_prompt,
                negative_prompt=shot.start_negative_prompt,
                width=w,
                height=h,
                output_path=start_file,
                reference_images=refs,
                metadata={
                    "shot_id": shot.shot_id,
                    "frame_tag": "START FRAME 01",
                    "shot_size": shot.six_w_one_h.which_shot_size,
                    "lens": shot.six_w_one_h.which_lens_and_aperture,
                    "camera_elevation": shot.spatial_blocking.camera_elevation,
                    "horizontal_zone": shot.spatial_blocking.horizontal_zone,
                    "body_view_angle": shot.spatial_blocking.body_view_angle.value,
                    "is_multi_character": shot.co_framing.is_multi_character,
                    "is_large_action": shot.anticlipping_pose.is_large_action,
                    "prop_active": any_prop_active,
                    "hero_colors": primary_char.signature_colors,
                    "rival_colors": rival_char.signature_colors,
                    "act_colors": act_colors,
                    "narration": shot.narration,
                },
            )
        )
        shot.start_keyframe_url = f"{self.store.asset_url(project_id, 'keyframes', start_file.name)}?v={ts}"

        # 5. Dual-Keyframe Mode: Also generate Frame N End Keyframe when selected in Which dimension!
        if shot.six_w_one_h.which_keyframe_strategy == KeyframeStrategy.FIRST_AND_LAST_FRAMES:
            shot.end_keyframe_prompt = self._assemble_frame_prompt(
                shot=shot,
                frame_spec=shot.end_frame,
                frame_role_label=f"END KEYFRAME (FRAME {shot.end_frame.frame_index:02d})",
                scene=scene,
                charter=charter,
                act_kelvin_note=act_kelvin_note,
                ledger_entry=ledger_entry,
                revision_prescription=revision_prescription,
            )
            end_refs = list(refs) + [
                ReferenceImage(
                    role="start_keyframe_anchor",
                    path=start_file,
                    label=f"Shot_{shot.shot_id:02d}_首帧基准",
                    weight=0.82,
                )
            ]
            end_file = pdir / f"shot_{shot.shot_id:02d}_end.png"
            await self.img.generate_image(
                ImageGenRequest(
                    kind="storyboard_keyframe",
                    prompt=shot.end_keyframe_prompt,
                    negative_prompt=shot.start_negative_prompt,
                    width=w,
                    height=h,
                    output_path=end_file,
                    reference_images=end_refs,
                    metadata={
                        "shot_id": shot.shot_id,
                        "frame_tag": f"END FRAME {shot.end_frame.frame_index:02d}",
                        "shot_size": shot.six_w_one_h.which_shot_size,
                        "lens": shot.six_w_one_h.which_lens_and_aperture,
                        "camera_elevation": shot.spatial_blocking.camera_elevation,
                        "horizontal_zone": shot.spatial_blocking.horizontal_zone,
                        "body_view_angle": shot.spatial_blocking.body_view_angle.value,
                        "is_multi_character": shot.co_framing.is_multi_character,
                        "is_large_action": shot.anticlipping_pose.is_large_action,
                        "prop_active": True,
                        "hero_colors": primary_char.signature_colors,
                        "rival_colors": rival_char.signature_colors,
                        "act_colors": act_colors,
                        "narration": shot.narration,
                    },
                )
            )
            shot.end_keyframe_url = f"{self.store.asset_url(project_id, 'keyframes', end_file.name)}?v={ts}"
        else:
            shot.end_keyframe_url = None
            shot.end_keyframe_prompt = ""

        dual_label = "首尾双关键帧 (Frame 01 + Frame N)" if shot.end_keyframe_url else "单首帧 (Frame 01)"
        await self.emit(
            project_id,
            "GENERATING_STORYBOARD",
            f"镜头 S{shot.shot_id:02d} 已渲染 {dual_label}（朝向={shot.spatial_blocking.body_view_angle.value}，挂载垫图={len(refs)}张）。",
            details={"shot_id": shot.shot_id, "dual_keyframes": bool(shot.end_keyframe_url)},
        )
        return shot
