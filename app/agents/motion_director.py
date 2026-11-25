"""Agent 07: Dynamic Physics, Secondary Motion & 6-DoF I2V Director (MotionDirectorAgent)."""

from __future__ import annotations

import time
from typing import Optional

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    AspectRatio,
    AssetBible,
    BodyViewAngle,
    CameraRigAndParallaxSpec,
    CharacterAssetCard,
    KeyframeStrategy,
    MotionHyperparameters,
    ShotMotionBlueprint,
    ShotSpec,
    ThreeLayerKinematicsSpec,
    VideoGenMode,
)


class MotionDirectorAgent(BaseStudioAgent):
    """07 动态物理运镜总监：I2V/KF2V路由、去静态三段时序、Google Flow原生提示词与真视频渲染."""

    agent_id = "agent_07_motion"
    agent_name = "07 动态物理运镜总监"

    @staticmethod
    def select_video_gen_mode(shot: ShotSpec) -> VideoGenMode:
        if shot.six_w_one_h.which_keyframe_strategy == KeyframeStrategy.FIRST_AND_LAST_FRAMES:
            return VideoGenMode.FIRST_LAST_KEYFRAME_KF2V
        if (
            shot.spatial_blocking.body_view_angle == BodyViewAngle.BACK
            or "旋身" in shot.six_w_one_h.physical_action_and_prop_event
            or shot.co_framing.is_multi_character
        ):
            return VideoGenMode.SUBJECT_REF_GUARDED_I2V
        return VideoGenMode.SINGLE_FRAME_I2V

    @staticmethod
    def compile_tri_slice_motion_prompt(shot: ShotSpec, char: CharacterAssetCard) -> str:
        """Purge static costume bloat; compile pure [Phase A -> Phase B -> Phase C] causal motion."""
        color_tag = char.signature_colors[0] if char.signature_colors else "crimson"
        subject_binder = f"Subject [{char.name} in {color_tag} attire]"
        mid_desc = (
            shot.mid_beat_frames[0].pose_and_expression
            if shot.mid_beat_frames
            else shot.six_w_one_h.physical_action_and_prop_event
        )
        return (
            f"{subject_binder} — SINGLE CONTINUOUS MECHANICAL ARC (NO MULTI-ACTION OVERLOAD): "
            f"[Phase A 0.0s-1.0s Subtle Anticipation]: From frozen StartFrame ({shot.start_frame.pose_and_expression[:48]}), "
            f"eyes shift 4 frames ahead of head movement, center of gravity settles slightly; "
            f"[Phase B 1.0s-3.0s Primary Action Release]: {mid_desc}; "
            f"[Phase C 3.0s-5.0s Damped Follow-Through]: Settles smoothly into {shot.end_frame.pose_and_expression[:52]}, "
            f"breathing chest micro-motion and lingering snow/light drift."
        )

    @staticmethod
    def compile_flow_english_prompt(
        shot: ShotSpec,
        char: CharacterAssetCard,
        mode: VideoGenMode,
        aspect_ratio: AspectRatio = AspectRatio.VERTICAL_9_16,
    ) -> str:
        """Compile native English Google Flow (`Video > Frames` Omni Flash / Veo) prompt with Native Audio."""
        orient = "Vertical 9:16" if aspect_ratio == AspectRatio.VERTICAL_9_16 else "Horizontal 16:9"
        is_kf2v = mode == VideoGenMode.FIRST_LAST_KEYFRAME_KF2V

        if shot.anticlipping_pose.is_large_action:
            cam_en = (
                "Locked-off cinema tripod with 90-degree crisp shutter angle (zero erratic camera shake), "
                "high-speed martial arts choreography: character pivots smoothly from the Start Frame unsheathing "
                "a rigid straight steel blade to deflect a flying iron dart in a burst of bright orange sparks, "
                "settling cleanly into the End Frame stance with 6-frame secondary pendulum sway on hair and crimson cloak."
            )
        elif shot.spatial_blocking.body_view_angle in (BodyViewAngle.BACK, BodyViewAngle.THREE_QUARTER_BACK):
            cam_en = (
                "Slow optical dolly-in over-the-shoulder shot from behind, maintaining strict 180-degree rear view "
                "(face never turns to camera), subtle breathing shoulder motion, drifting warm candle haze and 3D background parallax."
            )
        elif shot.six_w_one_h.temporal_speed_mode == "slow_mo_0.5x":
            cam_en = (
                "Locked macro 85mm shallow depth-of-field slow-motion (0.5x): sudden cold draft causes the miniature "
                "hexagonal silver bell earring on the left ear to tremble urgently while a meltwater droplet hangs in suspense."
            )
        elif shot.co_framing.is_multi_character:
            cam_en = (
                "Smooth Steadicam lateral tracking shot with genuine 3D foreground-to-background parallax: "
                "left character gestures warmly while right character steps slowly across wet wooden floorboards, "
                "snowflakes melting on shoulders under warm 3200K oil lamp vs 6800K blizzard doorway contrast."
            )
        else:
            cam_en = (
                "Smooth 35mm Cooke anamorphic dolly push-in with natural optical depth of field: "
                "eyes subtly shift 4 frames before micro head movement, warm specular highlights glide across brass fittings, "
                "drifting blizzard snow in the background."
            )

        frame_hint = (
            "Seamless physical keyframe interpolation from Start Frame to End Frame. "
            if is_kf2v
            else "Continuous natural live-action motion starting strictly from the Start Frame. "
        )

        if shot.narration.strip():
            audio_en = (
                f'Native audio: subtle howling blizzard wind outside wooden inn, character speaks in restrained cinematic Mandarin: "{shot.narration.strip()}".'
            )
        elif shot.anticlipping_pose.is_large_action:
            audio_en = (
                "Native audio: sharp metallic sword unsheathing ring, crisp steel-on-steel spark clang, "
                "deep taiko drum transient, and trailing silver bell chime."
            )
        elif shot.beat_phase == "escalation":
            audio_en = (
                "Native audio: sudden tense silence drop in music, urgent high-pitched silver wind-bell earring ringing over low blizzard wind."
            )
        else:
            audio_en = "Native audio: crisp brass latch click, boots stepping on wet pine wood, howling blizzard wind."

        return (
            f"{orient} 35mm live-action cinema film, 24fps photorealistic skin & fabric texture. "
            f"{frame_hint}{cam_en} Rigid straight weapon geometry, zero morphing. {audio_en}"
        )

    @staticmethod
    def synthesize_three_layer_kinematics(
        shot: ShotSpec, char: CharacterAssetCard
    ) -> ThreeLayerKinematicsSpec:
        pendulum_accs = [a.name for a in char.accessories if a.is_flexible_pendulum]
        acc_names = "、".join(pendulum_accs) if pendulum_accs else "发梢与衣摆"

        return ThreeLayerKinematicsSpec(
            primary_skeletal_drive=(
                "一级骨骼重心与眼先动法则(Eye-Lead Rule)：眼球视线先于颈椎转头提前4帧锁定目标，"
                "发力前支撑腿微沉蓄势(Anticipation)，收势时肩肘保留自然肌肉微缓冲，严禁石膏像急停"
            ),
            secondary_overlapping_motion=(
                f"二级柔性部件滞后跟随(4-8帧阻尼惯性)：主体躯干停稳后，角色佩戴的「{acc_names}」及外披下摆"
                "继续沿运动切线做两次微幅钟摆阻尼回荡再渐停，赋予真实物理重量感"
            ),
            tertiary_env_and_light_coupling=(
                f"三级环境流体与移动高光耦合：{shot.six_w_one_h.environmental_chain_reaction}；"
                "伴随人物角度微变，暖橘烛光在金属铜扣与剑脊表面产生连续流动高光扫掠(Moving Specular Sweep)"
            ),
        )

    @staticmethod
    def plan_camera_rig_and_counterbalance(shot: ShotSpec) -> CameraRigAndParallaxSpec:
        if shot.anticlipping_pose.is_large_action:
            return CameraRigAndParallaxSpec(
                rig_type="tripod_locked",
                movement_trajectory="高速大动作触发稳机位法则：三脚架锁死底座仅做<=5°顺势极缓微摇，杜绝反向甩镜",
                parallax_ratio_desc="固定视点下由前景飞溅雪沫/火星(高速)与背景静止木柱形成纯粹画内景深层次",
                rack_focus_plan="锁定f/2.8充足景深包裹人物与兵刃交击平面，禁止高速运动中盲目拉焦脱焦",
                counterbalance_rule_applied=(
                    "【动静互补防糊片铁律已激活】画内旋身拔剑速度极高，强制压制摄影机剧烈位移，配合90°快门角确保剑锋与手部边缘锐利不糊脸"
                ),
            )

        if shot.six_w_one_h.temporal_speed_mode == "slow_mo_0.5x":
            rig = "tripod_locked"
            traj = "死锁微距机位配合0.5x升格时间凝滞，放大耳畔风铃与悬浮雪粒微运动"
        elif shot.six_w_one_h.which_shot_size in ("MLS", "WS"):
            rig = "steadicam_follow"
            traj = "斯坦尼康轨道阻尼横移推进，平滑展现空间方位"
        else:
            rig = "dolly_track_smooth"
            traj = "精密轨道匀速推进12cm，产生真实光学透视变化而非2D数码缩放"

        return CameraRigAndParallaxSpec(
            rig_type=rig,  # type: ignore[arg-type]
            movement_trajectory=traj,
            parallax_ratio_desc=(
                "真三维视差速度比(3D Parallax 3.0 : 1.0 : 0.25)：前景门帘/热雾以3倍速掠向画框外缘，"
                "中景人物稳步占画，远景雕花木窗与房梁以0.25倍速微移，彻底消除PPT平面缩放感"
            ),
            rack_focus_plan=shot.six_w_one_h.which_focus_plane_and_shift,
            counterbalance_rule_applied="中低速叙事表演镜头，允许细腻轨道视差呼吸运动与画内微表情协同",
        )

    @staticmethod
    def tune_hyperparameters(shot: ShotSpec) -> MotionHyperparameters:
        if shot.anticlipping_pose.is_large_action:
            return MotionHyperparameters(
                motion_intensity=8,
                subject_fidelity_weight=0.75,
                shutter_angle_deg=90,
                recommended_raw_sec=5.0,
            )
        if shot.six_w_one_h.which_shot_size in ("ECU", "CU"):
            return MotionHyperparameters(
                motion_intensity=3,
                subject_fidelity_weight=0.89,
                shutter_angle_deg=180,
                recommended_raw_sec=5.0,
            )
        return MotionHyperparameters(
            motion_intensity=5,
            subject_fidelity_weight=0.82,
            shutter_angle_deg=180,
            recommended_raw_sec=5.0,
        )

    async def compile_motion_blueprints(
        self,
        project_id: str,
        shots: list[ShotSpec],
        bible: AssetBible,
        aspect_ratio: AspectRatio = AspectRatio.VERTICAL_9_16,
    ) -> list[ShotMotionBlueprint]:
        await self.emit(
            project_id,
            "COMPILING_MANIFEST",
            "正在编译全部镜头的 I2V/KF2V 模式路由、Google Flow 英文原生指令、牛顿三级物理联动与六自由度视差运镜参数…",
        )
        char_map = {c.character_id: c for c in bible.characters}
        results: list[ShotMotionBlueprint] = []

        for shot in shots:
            pchar = char_map.get(shot.six_w_one_h.primary_subject_id, bible.characters[0])
            mode = self.select_video_gen_mode(shot)
            tri_prompt = self.compile_tri_slice_motion_prompt(shot, pchar)
            flow_prompt = self.compile_flow_english_prompt(shot, pchar, mode, aspect_ratio=aspect_ratio)
            kinematics = self.synthesize_three_layer_kinematics(shot, pchar)
            cam_rig = self.plan_camera_rig_and_counterbalance(shot)
            hyper = self.tune_hyperparameters(shot)

            rigid_props = [p.name for p in pchar.carried_props if p.is_rigid_body]
            rigid_guard = (
                f"刚体几何不变形锁：随身器械「{'、'.join(rigid_props) or '竹骨伞剑'}」全程保持笔直刚性几何尺寸与恒定长度，"
                "严禁出现『橡胶剑弯曲』、握柄滑脱或人物头部触碰画框边缘截肢"
            )

            turnaround_refs = [
                c.turnaround_image_url
                for cid in shot.six_w_one_h.co_present_character_ids
                if (c := char_map.get(cid)) and c.turnaround_image_url
            ]

            results.append(
                ShotMotionBlueprint(
                    shot_id=shot.shot_id,
                    generation_mode=mode,
                    start_keyframe_ref=shot.start_keyframe_url,
                    end_keyframe_ref=shot.end_keyframe_url,
                    subject_turnaround_refs=turnaround_refs,
                    temporal_tri_slice_prompt=tri_prompt,
                    flow_english_prompt=flow_prompt,
                    kinematics=kinematics,
                    camera_rig=cam_rig,
                    rigid_prop_guardrail=rigid_guard,
                    dynamic_negative_prompt=(
                        "static frozen image, 2d digital zoom without parallax, morphing face, "
                        "bending rubber sword, melting fingers, disappearing earrings, flickering background"
                    ),
                    hyperparams=hyper,
                )
            )

        kf2v_count = sum(1 for m in results if m.generation_mode == VideoGenMode.FIRST_LAST_KEYFRAME_KF2V)
        await self.emit(
            project_id,
            "COMPILING_MANIFEST",
            f"动态物理运镜预编译完成：共 {len(results)} 镜（其中 {kf2v_count} 镜启用首尾双关键帧 KF2V 闭环锁死，已生成配套 Google Flow 英文原生指令）。",
            level="success",
        )
        return results

    async def render_single_shot_video(
        self,
        project_id: str,
        shot: ShotSpec,
        blueprint: ShotMotionBlueprint,
        prompt_override: str = "",
    ) -> str:
        """Invoke the active VideoProvider (`flow_browser` / `volcengine` / `kling` / `mock`) for one shot."""
        start_path = self.store.resolve_asset_url_to_path(shot.start_keyframe_url)
        if not start_path or not start_path.exists():
            raise FileNotFoundError(f"Shot S{shot.shot_id:02d} 缺少起始关键帧图像，无法启动图生视频。")

        end_path = None
        if blueprint.generation_mode == VideoGenMode.FIRST_LAST_KEYFRAME_KF2V and shot.end_keyframe_url:
            candidate_end = self.store.resolve_asset_url_to_path(shot.end_keyframe_url)
            if candidate_end and candidate_end.exists():
                end_path = candidate_end

        effective_prompt = (
            prompt_override.strip()
            or blueprint.flow_english_prompt
            or blueprint.temporal_tri_slice_prompt
        )
        if prompt_override.strip():
            blueprint.flow_english_prompt = prompt_override.strip()

        provider = self.video
        mode_tag = "首尾双帧 KF2V" if end_path else "单起始帧 I2V"
        await self.emit(
            project_id,
            "GENERATING_VIDEOS",
            f"正在通过 [{provider.vendor_name}] 渲染镜头 S{shot.shot_id:02d} 动态视频片段（{mode_tag} · 目标 {shot.duration_budget.final_duration_sec}s）…",
        )

        filename = f"shot_{shot.shot_id:02d}_{provider.vendor_name}.mp4"
        out_path = self.store.project_dir(project_id) / "clips" / filename
        await provider.generate_video(
            prompt=effective_prompt,
            start_image=start_path,
            output_path=out_path,
            end_image=end_path,
            duration_sec=max(3.0, shot.duration_budget.final_duration_sec + 0.6),
            motion_intensity=blueprint.hyperparams.motion_intensity,
        )

        ts = int(time.time() * 1000) % 1_000_000
        url = f"{self.store.asset_url(project_id, 'clips', filename)}?v={ts}"
        shot.video_clip_url = url
        await self.emit(
            project_id,
            "GENERATING_VIDEOS",
            f"镜头 S{shot.shot_id:02d} 动态视频片段生成完毕 -> `{filename}` ({out_path.stat().st_size // 1024} KB)。",
            level="success",
            details={"shot_id": shot.shot_id, "video_clip_url": url},
        )
        return url

    async def render_all_shot_videos(
        self,
        project_id: str,
        shots: list[ShotSpec],
        blueprints: list[ShotMotionBlueprint],
        skip_existing: bool = True,
    ) -> None:
        bp_map = {b.shot_id: b for b in blueprints}
        for shot in shots:
            if skip_existing and shot.video_clip_url:
                existing_file = self.store.resolve_asset_url_to_path(shot.video_clip_url)
                if existing_file and existing_file.exists() and existing_file.stat().st_size > 1000:
                    await self.emit(
                        project_id,
                        "GENERATING_VIDEOS",
                        f"镜头 S{shot.shot_id:02d} 已存在有效视频片段（含手动上传片段），直接复用。",
                    )
                    continue
            bp = bp_map.get(shot.shot_id)
            if not bp:
                continue
            await self.render_single_shot_video(project_id, shot, bp)
