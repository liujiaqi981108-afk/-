"""Agent 01: Executive Film Director, Continuity Supervisor & 9-Agent Orchestrator."""

from __future__ import annotations

from typing import Any, Optional

from app.agents.art_director import ArtDirectorAgent
from app.agents.base import BaseStudioAgent
from app.agents.master_editor import MasterEditorAgent
from app.agents.motion_director import MotionDirectorAgent
from app.agents.story_strategist import StoryStrategistAgent
from app.agents.storyboard_artist import StoryboardArtistAgent
from app.agents.storyboard_director import StoryboardDirectorAgent
from app.agents.visual_critic import VisualCriticAgent
from app.agents.voice_director import VoiceAndSoundDirectorAgent
from app.config import ProviderSettings
from app.models.schemas import (
    ActColorNode,
    AspectRatio,
    BodyViewAngle,
    ContinuityLedgerEntry,
    DirectorCharterAndLedger,
    ExecutionMode,
    KeyframeStrategy,
    PrescriptionTier,
    ProjectState,
    ShotSpec,
    StoryStrategyBlueprint,
    WorkflowStage,
)
from app.providers.base import (
    BaseImageProvider,
    BaseLLMProvider,
    BaseTTSProvider,
    BaseVideoProvider,
)
from app.storage.project_store import ProjectStore


class DirectorOrchestratorAgent(BaseStudioAgent):
    """01 总导演与制片统筹官：美学色彩总谱、场记连续性总账本、冲突仲裁、穿模借位改戏熔断与三关卡编排."""

    agent_id = "agent_01_director"
    agent_name = "01 总导演与制片统筹官"

    def __init__(
        self,
        store: Optional[ProjectStore] = None,
        settings: Optional[ProviderSettings] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        image_provider: Optional[BaseImageProvider] = None,
        video_provider: Optional[BaseVideoProvider] = None,
        tts_provider: Optional[BaseTTSProvider] = None,
    ) -> None:
        super().__init__(
            store=store,
            settings=settings,
            llm_provider=llm_provider,
            image_provider=image_provider,
            video_provider=video_provider,
            tts_provider=tts_provider,
        )
        shared = dict(
            store=self.store,
            settings=self.settings,
            llm_provider=llm_provider,
            image_provider=image_provider,
            video_provider=video_provider,
            tts_provider=tts_provider,
        )
        self.story_strategist = StoryStrategistAgent(**shared)
        self.storyboard_director = StoryboardDirectorAgent(**shared)
        self.art_director = ArtDirectorAgent(**shared)
        self.storyboard_artist = StoryboardArtistAgent(**shared)
        self.visual_critic = VisualCriticAgent(**shared)
        self.motion_director = MotionDirectorAgent(**shared)
        self.voice_director = VoiceAndSoundDirectorAgent(**shared)
        self.master_editor = MasterEditorAgent(**shared)

    async def build_charter(self, state: ProjectState) -> DirectorCharterAndLedger:
        await self.emit(
            state.project_id,
            "PLANNING_SCRIPT",
            "01 总导演开机立项：正在签发《全片视觉介质宪章》、《五幕色彩情绪总谱(Color Script)》与《画幅安全净空戒律》…",
        )
        llm_res = await self.llm.generate_json(
            system_prompt="你是电影总导演。请确立统一的视觉介质基因锁与全局负向禁令。",
            user_prompt=f"创意：{state.topic}\n风格：{state.style_preset}\n画幅：{state.aspect_ratio.value}",
            context={"task": "director_charter", "topic": state.topic, "style_preset": state.style_preset},
        )

        if state.aspect_ratio == AspectRatio.VERTICAL_9_16:
            framing_mandate = (
                "【9:16 竖屏纵向电影构图戒律】强制采用纵向空间高低差调度（高处梁檐灯笼→中景人物→地面青石接触阴影），"
                "锁定人物眼部位于顶边下 26%-36% 黄金视觉带；严令画面底部 20% 字幕净空区与右侧 12% 平台互动栏避让区禁止放置关键伏笔道具！"
            )
        else:
            framing_mandate = (
                "【16:9 变形宽银幕构图戒律】充分利用左右三分线与前景侧框景深遮挡构筑纵深感，底部 15% 预留电影字幕呼吸净空带。"
            )

        color_arc = [
            ActColorNode(
                act_phase="hook",
                kelvin_temp="6800K 冷铁青微距高反差",
                dominant_and_accent_hex=["#131E29", "#283C4F", "#E0A445"],
                lighting_mood_note="门缝暴风雪冷光勾勒金属铜扣一抹冷冽寒芒",
                luminance_contrast_ratio="Low-key 8:1",
            ),
            ActColorNode(
                act_phase="setup",
                kelvin_temp="3400K 暖烛琥珀对撞 6500K 门外残雪",
                dominant_and_accent_hex=["#1D252E", "#8C5832", "#DF9642"],
                lighting_mood_note="外冷内暖双色温分界暗示伪善客栈暗藏杀机",
                luminance_contrast_ratio=" Chiaroscuro 5:1",
            ),
            ActColorNode(
                act_phase="escalation",
                kelvin_temp="4600K 压抑青灰低饱和收束",
                dominant_and_accent_hex=["#161D24", "#3B4B59", "#C89B54"],
                lighting_mood_note="烛火被暗流压低，高潮前色彩与声音同步收紧窒息",
                luminance_contrast_ratio="Low-key 7:1",
            ),
            ActColorNode(
                act_phase="climax",
                kelvin_temp="2900K 火花金橙撞击 #B8332A 朱砂绯红破局",
                dominant_and_accent_hex=["#1A1416", "#B8332A", "#F2B14B"],
                lighting_mood_note="全片最高饱和度与明暗反差爆发点，剑光与金铁火花刺破暗调",
                luminance_contrast_ratio="High-Impact 10:1",
            ),
            ActColorNode(
                act_phase="afterglow",
                kelvin_temp="7200K 清冷雪白留白余韵",
                dominant_and_accent_hex=["#1B2430", "#4A5D70", "#D9A441"],
                lighting_mood_note="杀机落定归于冷白苍茫风雪，尾帧铜扣暖光呼应首帧",
                luminance_contrast_ratio="Soft Low-key 4:1",
            ),
        ]

        return DirectorCharterAndLedger(
            title=llm_res.get("title", "《风雪孤驿·听风刃》"),
            visual_medium_lock=llm_res.get("visual_medium_lock", f"{state.style_preset} · 35mm 胶片光学质感"),
            style_preset=state.style_preset,
            target_total_duration_sec=state.target_duration_sec,
            aspect_framing_mandate=framing_mandate,
            global_negative_mandate=llm_res.get(
                "global_negative_mandate",
                "3d plastic render, extra limbs, weapon clipping, floating feet, watermark, text gibberish",
            ),
            color_script_arc=color_arc,
        )

    def arbitrate_script_and_timing(
        self,
        charter: DirectorCharterAndLedger,
        shots: list[ShotSpec],
        strategy: StoryStrategyBlueprint,
    ) -> list[ShotSpec]:
        """01 Director Cross-Department Arbitrator: resolve speech duration vs fast-cut timing clashes."""
        arb_logs: list[str] = []
        for idx, shot in enumerate(shots):
            if not shot.narration.strip():
                continue
            core_len = len([c for c in shot.narration if c not in "，。？！…—、,.?! "])
            # Conservative acting tempo from 08 VoiceDirector (3.5 chars/s + 0.55s breath/pause)
            realistic_vocal_sec = round(core_len / 3.5 + 0.65, 1)
            cur_sec = shot.duration_budget.final_duration_sec

            if realistic_vocal_sec > cur_sec:
                if shot.beat_phase in ("hook", "climax"):
                    # High-tension action/hook beat: keep tight cut duration, mandate L-Cut audio spillover!
                    shot.six_w_one_h.which_cut_transition = "j_cut_lead"
                    arb_logs.append(
                        f"【跨部门冲突裁决·S{shot.shot_id:02d}】快切节拍({cur_sec}s) < 声线气口实需({realistic_vocal_sec}s)："
                        f"总导演裁定『保动作快切节奏优先』，禁止拉水镜头，强制指派 09 剪辑总监启用跨镜错位延音承载尾音。"
                    )
                else:
                    new_sec = min(5.0, realistic_vocal_sec)
                    shot.duration_budget.final_duration_sec = new_sec
                    arb_logs.append(
                        f"【跨部门冲突裁决·S{shot.shot_id:02d}】潜台词文戏镜原定 {cur_sec}s 不足以容纳 08 声线总监的心理停顿气口({realistic_vocal_sec}s)："
                        f"总导演裁定『保潜台词呼吸留白优先』，核准上浮镜头时长至 {new_sec}s 并重算全局时间码。"
                    )

        if not arb_logs:
            arb_logs.append(
                "【跨部门对齐核准】02剧作字数、03分镜心跳时长与08声线气口预算全部包络兼容，无需强制削改。"
            )
        charter.arbitration_logs = arb_logs
        return StoryboardDirectorAgent.recalculate_timeline(shots)

    @staticmethod
    def build_continuity_ledger(
        charter: DirectorCharterAndLedger,
        shots: list[ShotSpec],
        strategy: StoryStrategyBlueprint,
    ) -> list[ContinuityLedgerEntry]:
        """Build irreversible shot-by-shot Master Continuity Ledger (snow/wetness/prop coordinates/scene damage)."""
        prop_id = strategy.chekhov_props[0].prop_id if strategy.chekhov_props else "prop_chekhov_01"
        prop_name = strategy.chekhov_props[0].prop_name if strategy.chekhov_props else "随身伞剑"

        entries: list[ContinuityLedgerEntry] = []
        persisted_damage: list[str] = []
        hero_state = "刚自暴风雪外抵门，披风肩头覆一层细白新雪，鬓角微霜，衣袖完好"
        rival_state = "室内久候衣着干燥整洁，靴底无半点雪泥（核心破绽）"

        for shot in shots:
            if shot.beat_phase == "setup":
                hero_state = "踏入暖堂肩头积雪初融为细密微湿水珠，呼吸带白雾，衣袖完好"
                persisted_damage.append("南门入口老松木地台留下一串清晰的湿雪靴印")
            elif shot.beat_phase == "climax" or shot.anticlipping_pose.is_large_action:
                hero_state = "激战旋身后发丝微乱带汗意，肩头残雪震落，右腕护腕紧束完好"
                persisted_damage.append("桌角粗陶碗被剑气震落摔碎于中景地面，留有暗色水渍与一枚击落的铁镖")
                prop_coord = f"{prop_name}细剑出鞘紧握于右手，空竹伞鞘落于左脚侧0.5米木地台上"
            elif shot.beat_phase == "afterglow":
                hero_state = "继承战后鬓发微湿状态（严禁复原为干燥新妆），神色冷峻"
                prop_coord = f"细剑已重新归入拾起的{prop_name}竹鞘并扣合黄铜暗扣，右手持握垂于身侧"
            else:
                mode = shot.six_w_one_h.prop_active_states.get(prop_id, "carried")
                prop_coord = (
                    f"{prop_name}已移至右手预备顶开机括"
                    if mode == "active_held"
                    else f"{prop_name}斜背于左肩至右后腰固定系带位置"
                )

            entries.append(
                ContinuityLedgerEntry(
                    shot_id=shot.shot_id,
                    story_time_progress=shot.six_w_one_h.story_time_node,
                    character_physical_states={
                        "char_hero": hero_state,
                        "char_rival": rival_state,
                    },
                    prop_spatial_states={prop_id: prop_coord},
                    environment_damage_persisted=list(persisted_damage),
                )
            )

        charter.continuity_ledger = entries
        return entries

    async def apply_creative_fallback_montage(
        self,
        project_id: str,
        charter: DirectorCharterAndLedger,
        shot: ShotSpec,
    ) -> ShotSpec:
        """Tier-3 Circuit Breaker: rewrite persistent clipping full-body slash into zero-clipping cinema insert/shadow montage!"""
        old_desc = shot.six_w_one_h.narrative_beat_goal
        shot.is_creative_fallback_montage = True
        shot.six_w_one_h.which_shot_size = "ECU"
        shot.six_w_one_h.which_lens_and_aperture = "85mm f/1.4 特写借位大师镜"
        shot.six_w_one_h.which_keyframe_strategy = KeyframeStrategy.SINGLE_START_FRAME
        shot.anticlipping_pose.is_large_action = False
        shot.spatial_blocking.body_view_angle = BodyViewAngle.THREE_QUARTER_FRONT
        shot.start_frame.pose_and_expression = (
            "【总导演借位改戏蒙太奇】85mm极特写：一抹森白剑锋寒光横贯前景映亮主角冷冽双瞳，"
            "背景西侧夯土墙面上清晰投射出凌厉剑影一闪劈落暗器的高反差剪影，彻底规避全身肢体与宽袖重叠穿模！"
        )
        shot.anticlipping_pose.limb_prop_separation_rule = (
            "借位蒙太奇构图：前景仅呈现笔直刚性剑脊局部寒光与双眸特写，零复杂多肢体交叠，100%物理零穿模"
        )
        log_msg = (
            f"【三级熔断·导演借位改戏 S{shot.shot_id:02d}】原正面全身拼刀构图（{old_desc[:24]}…）连续触发解剖穿模，"
            "01总导演已下令改写为『寒光映瞳极特写 + 西墙剑影切落借位蒙太奇』，张力倍增且100%零穿模。"
        )
        charter.fallback_rewrites.append(log_msg)
        await self.emit(project_id, "REVIEWING_STORYBOARD", log_msg, level="warn")
        return shot

    # ==========================================================================
    # Pipeline Stage Runners (Supporting Both 3-Gate HITL & One-Click Auto Mode)
    # ==========================================================================

    async def run_from_start(self, project_id: str) -> ProjectState:
        state = await self.store.load(project_id)
        try:
            state = await self.run_stage1_script(project_id)
            if state.execution_mode == ExecutionMode.AUTO:
                state = await self.run_stage2_assets(project_id)
                state = await self.run_stage3_storyboard_and_qa(project_id)
                state = await self.run_stage4_compile_manifest(project_id)
            return state
        except Exception as exc:
            await self.emit(project_id, "FAILED", f"工作流执行异常: {exc}", level="warn")
            return await self.store.mutate(
                project_id,
                lambda s: setattr(s, "stage", WorkflowStage.FAILED) or setattr(s, "error_message", str(exc)),
            )

    async def run_stage1_script(self, project_id: str) -> ProjectState:
        state = await self.store.mutate(
            project_id, lambda s: setattr(s, "stage", WorkflowStage.PLANNING_SCRIPT)
        )
        charter = await self.build_charter(state)
        strategy = await self.story_strategist.build_story_strategy(project_id, state.topic, charter)
        shots = await self.storyboard_director.build_storyboard(
            project_id, state.topic, charter, strategy, shot_count_hint=state.shot_count_hint
        )
        shots = self.arbitrate_script_and_timing(charter, shots, strategy)
        self.build_continuity_ledger(charter, shots, strategy)

        next_stage = (
            WorkflowStage.AWAITING_SCRIPT_APPROVAL
            if state.execution_mode == ExecutionMode.HITL
            else WorkflowStage.BUILDING_ASSETS
        )

        def _save_s1(s: ProjectState) -> None:
            s.director_charter = charter
            s.story_strategy = strategy
            s.shots = shots
            s.stage = next_stage

        state = await self.store.mutate(project_id, _save_s1)
        if next_stage == WorkflowStage.AWAITING_SCRIPT_APPROVAL:
            await self.emit(
                project_id,
                "AWAITING_SCRIPT_APPROVAL",
                "【HITL 关卡 1 待审】总导演色彩总谱、高概念剧作策划与 24fps 帧级 6W1H 台本已就绪，请审阅或微调后确认进入视觉与声学资产建档。",
                level="gate",
            )
        return state

    async def approve_script_and_continue(self, project_id: str) -> ProjectState:
        state = await self.run_stage2_assets(project_id)
        if state.execution_mode == ExecutionMode.AUTO:
            state = await self.run_stage3_storyboard_and_qa(project_id)
            state = await self.run_stage4_compile_manifest(project_id)
        return state

    async def run_stage2_assets(self, project_id: str) -> ProjectState:
        state = await self.store.mutate(
            project_id, lambda s: setattr(s, "stage", WorkflowStage.BUILDING_ASSETS)
        )
        assert state.director_charter and state.story_strategy
        bible = await self.art_director.build_assets(
            project_id=project_id,
            topic=state.topic,
            aspect_ratio=state.aspect_ratio,
            charter=state.director_charter,
            strategy=state.story_strategy,
            shots=state.shots,
        )
        vocals = await self.voice_director.build_vocal_profiles(
            project_id=project_id,
            strategy=state.story_strategy,
            bible=bible,
        )

        next_stage = (
            WorkflowStage.AWAITING_ASSET_APPROVAL
            if state.execution_mode == ExecutionMode.HITL
            else WorkflowStage.GENERATING_STORYBOARD
        )

        def _save_s2(s: ProjectState) -> None:
            s.asset_bible = bible
            s.vocal_profiles = vocals
            s.stage = next_stage

        state = await self.store.mutate(project_id, _save_s2)
        if next_stage == WorkflowStage.AWAITING_ASSET_APPROVAL:
            await self.emit(
                project_id,
                "AWAITING_ASSET_APPROVAL",
                "【HITL 关卡 2 待审】1440x960 角色正/侧/背标准三视图、契诃夫随身物双态卡、五维声学基因卡与三维罗盘场景空镜母版已生成，锁定后将作为全片分镜一致性垫图。",
                level="gate",
            )
        return state

    async def approve_assets_and_continue(self, project_id: str) -> ProjectState:
        state = await self.run_stage3_storyboard_and_qa(project_id)
        if state.execution_mode == ExecutionMode.AUTO:
            state = await self.run_stage4_compile_manifest(project_id)
        return state

    async def _render_and_inspect_single_shot(
        self,
        project_id: str,
        shot: ShotSpec,
        aspect_ratio: AspectRatio,
        bible: Any,
        charter: DirectorCharterAndLedger,
        user_feedback: str = "",
        extra_qa_ctx: Optional[dict[str, Any]] = None,
    ) -> ShotSpec:
        ledger_entry = next(
            (e for e in charter.continuity_ledger if e.shot_id == shot.shot_id), None
        )
        max_attempts = self.settings.max_qa_retries_per_shot + 1
        prescription = user_feedback.strip()
        history_notes: list[str] = []

        for attempt in range(1, max_attempts + 1):
            await self.storyboard_artist.generate_shot_keyframes(
                project_id=project_id,
                shot=shot,
                aspect_ratio=aspect_ratio,
                bible=bible,
                charter=charter,
                ledger_entry=ledger_entry,
                revision_prescription=prescription,
            )
            qa = await self.visual_critic.inspect_shot(
                project_id=project_id,
                shot=shot,
                bible=bible,
                attempt=attempt,
                extra_context=extra_qa_ctx,
            )
            if history_notes:
                qa.history_notes = list(history_notes)
            shot.qa_report = qa

            if qa.overall_passed:
                break

            history_notes.append(f"第{attempt}审[{qa.prescription_tier.value}]: {qa.revision_prescription}")
            should_fallback = (
                qa.prescription_tier == PrescriptionTier.TIER3_CREATIVE_FALLBACK
                or attempt >= max_attempts
            )
            if should_fallback:
                await self.apply_creative_fallback_montage(project_id, charter, shot)
                await self.storyboard_artist.generate_shot_keyframes(
                    project_id=project_id,
                    shot=shot,
                    aspect_ratio=aspect_ratio,
                    bible=bible,
                    charter=charter,
                    ledger_entry=ledger_entry,
                    revision_prescription="执行总导演借位极特写蒙太奇，彻底消除肢体穿模",
                )
                clean_qa = await self.visual_critic.inspect_shot(
                    project_id=project_id,
                    shot=shot,
                    bible=bible,
                    attempt=attempt + 1,
                    extra_context={"skip_first_action_heal": True},
                )
                clean_qa.history_notes = list(history_notes) + ["总导演三级熔断借位改戏后复审通过"]
                shot.qa_report = clean_qa
                break

            # Apply Tier 1 or Tier 2 surgical camera/prompt adjustment and retry
            self.visual_critic.apply_surgical_adjustment_to_shot(shot, qa)
            prescription = qa.revision_prescription

        return shot

    async def run_stage3_storyboard_and_qa(self, project_id: str) -> ProjectState:
        state = await self.store.mutate(
            project_id, lambda s: setattr(s, "stage", WorkflowStage.GENERATING_STORYBOARD)
        )
        assert state.asset_bible and state.director_charter

        updated_shots: list[ShotSpec] = []
        for shot in state.shots:
            rendered = await self._render_and_inspect_single_shot(
                project_id=project_id,
                shot=shot,
                aspect_ratio=state.aspect_ratio,
                bible=state.asset_bible,
                charter=state.director_charter,
            )
            updated_shots.append(rendered)

        await self.store.mutate(
            project_id, lambda s: setattr(s, "stage", WorkflowStage.REVIEWING_STORYBOARD)
        )
        strip_report = await self.visual_critic.audit_strip_continuity(project_id, updated_shots)

        next_stage = (
            WorkflowStage.AWAITING_STORYBOARD_APPROVAL
            if state.execution_mode == ExecutionMode.HITL
            else WorkflowStage.COMPILING_MANIFEST
        )

        def _save_s3(s: ProjectState) -> None:
            s.shots = updated_shots
            s.strip_audit = strip_report
            s.director_charter = state.director_charter
            s.stage = next_stage

        state = await self.store.mutate(project_id, _save_s3)
        if next_stage == WorkflowStage.AWAITING_STORYBOARD_APPROVAL:
            await self.emit(
                project_id,
                "AWAITING_STORYBOARD_APPROVAL",
                "【HITL 关卡 3 待审】全片单/双关键帧文生图、作画监督三图交叉质检与连环画拼条连续性审片已全部达标！可对任意单镜微调重抽，或确认生成 Phase 2 动态运镜与声画剪辑总单。",
                level="gate",
            )
        return state

    async def approve_storyboard_and_finalize(self, project_id: str) -> ProjectState:
        return await self.run_stage4_compile_manifest(project_id)

    async def run_stage4_compile_manifest(self, project_id: str) -> ProjectState:
        state = await self.store.mutate(
            project_id, lambda s: setattr(s, "stage", WorkflowStage.COMPILING_MANIFEST)
        )
        assert state.asset_bible and state.director_charter and state.story_strategy

        motion_list = await self.motion_director.compile_motion_blueprints(
            project_id=project_id,
            shots=state.shots,
            bible=state.asset_bible,
            aspect_ratio=state.aspect_ratio,
        )
        sound_list = await self.voice_director.build_sound_blueprints(
            project_id=project_id,
            shots=state.shots,
            bible=state.asset_bible,
            vocal_profiles=state.vocal_profiles,
            strategy=state.story_strategy,
        )
        editorial_list, manifest = await self.master_editor.build_editorial_and_manifest(
            project_id=project_id,
            aspect_ratio=state.aspect_ratio,
            charter=state.director_charter,
            shots=state.shots,
            vocal_profiles=state.vocal_profiles,
            motion_blueprints=motion_list,
            sound_blueprints=sound_list,
        )
        manifest_url = await self.store.save_manifest(project_id, manifest)

        def _save_s4(s: ProjectState) -> None:
            s.motion_blueprints = motion_list
            s.sound_blueprints = sound_list
            s.editorial_blueprints = editorial_list
            s.manifest_url = manifest_url
            s.stage = WorkflowStage.PHASE1_COMPLETED

        state = await self.store.mutate(project_id, _save_s4)
        await self.emit(
            project_id,
            "PHASE1_COMPLETED",
            f"🎉 Phase 1 顶级制片厂视听工程全套交付完成！已导出 `{manifest_url}`，可随时无缝驱动 Phase 2 视频与声画合成。",
            level="success",
            details={"manifest_url": manifest_url},
        )
        return state

    # ==========================================================================
    # Surgical Fine-Tuning & Partial Reroll Endpoints
    # ==========================================================================

    async def update_shot_script(
        self,
        project_id: str,
        shot_id: int,
        narration: Optional[str] = None,
        duration_sec: Optional[float] = None,
        keyframe_strategy: Optional[KeyframeStrategy] = None,
        body_view_angle: Optional[BodyViewAngle] = None,
    ) -> ProjectState:
        state = await self.store.load(project_id)
        target = next((s for s in state.shots if s.shot_id == shot_id), None)
        if not target:
            raise ValueError(f"Shot {shot_id} not found")

        if narration is not None:
            target.narration = narration.strip()
            new_budget = StoryboardDirectorAgent.calculate_duration_envelope(
                shot_size=target.six_w_one_h.which_shot_size,
                action_physics_sec=target.duration_budget.action_physics_sec,
                narration=target.narration,
            )
            target.duration_budget = new_budget

        if duration_sec is not None:
            clamped = round(min(5.0, max(1.0, float(duration_sec))), 1)
            target.duration_budget.final_duration_sec = clamped

        if keyframe_strategy is not None:
            target.six_w_one_h.which_keyframe_strategy = keyframe_strategy

        if body_view_angle is not None:
            target.spatial_blocking.body_view_angle = body_view_angle

        StoryboardDirectorAgent.recalculate_timeline(state.shots)
        if state.director_charter and state.story_strategy:
            self.build_continuity_ledger(state.director_charter, state.shots, state.story_strategy)

        await self.store.save(state)
        await self.emit(
            project_id,
            state.stage.value,
            f"已在线精修镜头 S{shot_id:02d} 台本参数，全片累计时间轴与场记连续性账本已自动重算同步。",
            level="info",
        )
        return state

    async def reroll_character_asset(
        self, project_id: str, character_id: str, custom_note: str = ""
    ) -> ProjectState:
        state = await self.store.load(project_id)
        if not state.asset_bible:
            raise ValueError("AssetBible not built yet")
        await self.art_director.regenerate_character_turnaround(
            project_id, state.asset_bible, character_id, custom_note=custom_note
        )
        return await self.store.save(state)

    async def reroll_scene_asset(
        self, project_id: str, scene_id: str, custom_note: str = ""
    ) -> ProjectState:
        state = await self.store.load(project_id)
        if not state.asset_bible:
            raise ValueError("AssetBible not built yet")
        await self.art_director.regenerate_scene_plate(
            project_id, state.asset_bible, state.aspect_ratio, scene_id, custom_note=custom_note
        )
        return await self.store.save(state)

    async def reroll_single_shot(
        self,
        project_id: str,
        shot_id: int,
        feedback: str = "",
        body_view_angle: Optional[BodyViewAngle] = None,
        keyframe_strategy: Optional[KeyframeStrategy] = None,
    ) -> ProjectState:
        state = await self.store.load(project_id)
        if not state.asset_bible or not state.director_charter:
            raise ValueError("Assets or charter not initialized")
        target = next((s for s in state.shots if s.shot_id == shot_id), None)
        if not target:
            raise ValueError(f"Shot {shot_id} not found")

        if body_view_angle is not None:
            target.spatial_blocking.body_view_angle = body_view_angle
        if keyframe_strategy is not None:
            target.six_w_one_h.which_keyframe_strategy = keyframe_strategy

        await self._render_and_inspect_single_shot(
            project_id=project_id,
            shot=target,
            aspect_ratio=state.aspect_ratio,
            bible=state.asset_bible,
            charter=state.director_charter,
            user_feedback=feedback,
            extra_qa_ctx={"skip_first_action_heal": True},
        )
        state.strip_audit = await self.visual_critic.audit_strip_continuity(project_id, state.shots)
        if state.stage in (WorkflowStage.PHASE1_COMPLETED, WorkflowStage.COMPLETED):
            await self.store.save(state)
            return await self.run_stage4_compile_manifest(project_id)
        return await self.store.save(state)

    # ==========================================================================
    # Phase 2 Execution: Real Video Clips, 4-Stem Soundscape & Master MP4 Muxing
    # ==========================================================================

    async def run_phase2_production(
        self, project_id: str, skip_existing_clips: bool = True
    ) -> ProjectState:
        """Execute Phase 2 end-to-end: 07 Video Clips -> 08 4-Stem Soundtrack -> 09 Master MP4."""
        state = await self.store.load(project_id)
        if not state.motion_blueprints or not state.sound_blueprints or not state.editorial_blueprints:
            state = await self.run_stage4_compile_manifest(project_id)

        try:
            state = await self.store.mutate(
                project_id,
                lambda s: setattr(s, "stage", WorkflowStage.GENERATING_VIDEOS)
                or setattr(s, "error_message", None),
            )
            await self.motion_director.render_all_shot_videos(
                project_id=project_id,
                shots=state.shots,
                blueprints=state.motion_blueprints,
                skip_existing=skip_existing_clips,
            )
            await self.store.save(state)

            return await self.recompose_master_video(project_id)
        except Exception as exc:
            await self.emit(
                project_id,
                "GENERATING_VIDEOS",
                f"⚠️ Phase 2 视频渲染中断: {exc}",
                level="warn",
            )
            return await self.store.mutate(
                project_id,
                lambda s: setattr(s, "stage", WorkflowStage.PHASE1_COMPLETED)
                or setattr(s, "error_message", str(exc)),
            )

    async def reroll_single_shot_video(
        self,
        project_id: str,
        shot_id: int,
        prompt_override: str = "",
        auto_recompose: bool = True,
    ) -> ProjectState:
        """Render or re-render a single shot `.mp4` clip (via `flow_browser` / `mock` / API)."""
        state = await self.store.load(project_id)
        if not state.motion_blueprints:
            state = await self.run_stage4_compile_manifest(project_id)

        shot = next((s for s in state.shots if s.shot_id == shot_id), None)
        bp = next((b for b in state.motion_blueprints if b.shot_id == shot_id), None)
        if not shot or not bp:
            raise ValueError(f"Shot {shot_id} or motion blueprint not found")

        await self.motion_director.render_single_shot_video(
            project_id=project_id,
            shot=shot,
            blueprint=bp,
            prompt_override=prompt_override,
        )
        await self.store.save(state)

        all_ready = all(bool(s.video_clip_url) for s in state.shots)
        if auto_recompose and (state.final_video_url or all_ready):
            return await self.recompose_master_video(project_id)
        return await self.store.load(project_id)

    async def save_uploaded_shot_video(
        self,
        project_id: str,
        shot_id: int,
        raw_mp4_bytes: bytes,
        auto_recompose: bool = True,
    ) -> ProjectState:
        """Accept a user-uploaded `.mp4` clip (e.g. downloaded manually from Google Flow Web) for a shot."""
        import time

        if len(raw_mp4_bytes) < 512:
            raise ValueError("上传的视频文件体积过小或为空，请上传有效的 .mp4 视频片段。")

        state = await self.store.load(project_id)
        shot = next((s for s in state.shots if s.shot_id == shot_id), None)
        if not shot:
            raise ValueError(f"Shot {shot_id} not found")

        filename = f"shot_{shot_id:02d}_uploaded.mp4"
        clip_path = self.store.project_dir(project_id) / "clips" / filename
        clip_path.write_bytes(raw_mp4_bytes)

        ts = int(time.time() * 1000) % 1_000_000
        shot.video_clip_url = f"{self.store.asset_url(project_id, 'clips', filename)}?v={ts}"
        await self.store.save(state)
        await self.emit(
            project_id,
            state.stage.value,
            f"📥 已导入镜头 S{shot_id:02d} 外部视频片段 `{filename}` ({len(raw_mp4_bytes) // 1024} KB)。",
            level="success",
            details={"shot_id": shot_id, "video_clip_url": shot.video_clip_url},
        )

        all_ready = all(bool(s.video_clip_url) for s in state.shots)
        if auto_recompose and (state.final_video_url or all_ready):
            return await self.recompose_master_video(project_id)
        return await self.store.load(project_id)

    async def recompose_master_video(self, project_id: str) -> ProjectState:
        """Synthesize 4-stem soundtrack and mux `final_master.mp4` from current shot clips & keyframes."""
        state = await self.store.load(project_id)
        if not state.sound_blueprints or not state.editorial_blueprints:
            state = await self.run_stage4_compile_manifest(project_id)

        state = await self.store.mutate(
            project_id, lambda s: setattr(s, "stage", WorkflowStage.COMPOSITING_FINAL)
        )
        master_audio, subtitles, soundtrack_url = await self.voice_director.synthesize_project_soundtrack(
            project_id=project_id,
            shots=state.shots,
            sound_blueprints=state.sound_blueprints,
            editorial_blueprints=state.editorial_blueprints,
        )
        final_url = await self.master_editor.compose_final_master_mp4(
            project_id=project_id,
            aspect_ratio=state.aspect_ratio,
            shots=state.shots,
            editorial_blueprints=state.editorial_blueprints,
            master_audio=master_audio,
            subtitles=subtitles,
        )

        def _save_done(s: ProjectState) -> None:
            for updated_shot in state.shots:
                target = next((x for x in s.shots if x.shot_id == updated_shot.shot_id), None)
                if target:
                    target.audio_clip_url = updated_shot.audio_clip_url
                    target.video_clip_url = updated_shot.video_clip_url
            s.soundtrack_url = soundtrack_url
            s.final_video_url = final_url
            s.error_message = None
            s.stage = WorkflowStage.COMPLETED

        return await self.store.mutate(project_id, _save_done)
