"""Agent 03: Storyboard & Frame-Level Scheduling Director (StoryboardDirectorAgent)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    AntiClippingPoseSpec,
    BodyViewAngle,
    DirectorCharterAndLedger,
    DurationBudgetBreakdown,
    FrameSnapshotSpec,
    KeyframeStrategy,
    MultiCharacterCoFramingSpec,
    ShotSixWOneHMatrix,
    ShotSpec,
    SpatialBlockingSpec,
    StoryStrategyBlueprint,
)
from app.providers.mock import parse_topic_seeds

VISUAL_READ_BASELINES: dict[str, float] = {
    "ECU": 1.3,
    "CU": 1.6,
    "MCU": 2.2,
    "MS": 2.7,
    "MLS": 3.3,
    "WS": 4.0,
}


class StoryboardDirectorAgent(BaseStudioAgent):
    """03 视听分镜与帧级调度导演：心跳时长波形、四维科学定长、6W1H+Which矩阵与24fps首中尾帧拆解."""

    agent_id = "agent_03_storyboard"
    agent_name = "03 视听分镜与帧级导演"

    @staticmethod
    def calculate_duration_envelope(
        shot_size: str,
        action_physics_sec: float,
        narration: str,
        chars_per_sec: float = 4.0,
        silence_before_ms: int = 350,
    ) -> DurationBudgetBreakdown:
        """Scientific 4-constraint shot duration envelope clamped to [1.0s, 5.0s]."""
        vis_sec = round(VISUAL_READ_BASELINES.get(shot_size, 2.5), 2)
        act_sec = round(max(0.8, action_physics_sec), 2)

        core_chars = [c for c in (narration or "").strip() if c not in "，。？！…—、,.?! "]
        if core_chars:
            speech_sec = round(len(core_chars) / max(2.5, chars_per_sec) + (silence_before_ms / 1000.0) + 0.45, 2)
        else:
            speech_sec = 0.0

        raw_env = max(vis_sec, act_sec, speech_sec)
        final_sec = round(min(5.0, max(1.0, raw_env)), 1)
        frames_24 = max(24, int(round(final_sec * 24)))
        trim_in = 6 if frames_24 <= 108 else 1
        trim_out = min(120, trim_in + frames_24 - 1)

        rationale = (
            f"包络定长 max(景别{shot_size}扫视 {vis_sec}s, 动作物理 {act_sec}s, "
            f"台词气口 {speech_sec}s) → 核定 {final_sec}s ({frames_24}帧@24fps)"
        )
        return DurationBudgetBreakdown(
            visual_read_sec=vis_sec,
            action_physics_sec=act_sec,
            speech_plus_breath_sec=speech_sec,
            final_duration_sec=final_sec,
            total_frames_24fps=frames_24,
            i2v_raw_generation_sec=5.0,
            trim_in_frame=trim_in,
            trim_out_frame=trim_out,
            duration_rationale=rationale,
        )

    @classmethod
    def split_overlong_action_drafts(cls, drafts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
        """Automatically split any single draft whose physical action exceeds 5.0s I2V ceiling."""
        result: list[dict[str, Any]] = []
        split_logs: list[str] = []
        for d in drafts:
            act_sec = float(d.get("action_physics_sec", 2.4))
            if act_sec > 5.0:
                part1 = dict(d)
                part2 = dict(d)
                part1["action_physics_sec"] = round(act_sec * 0.42, 1)
                part1["shot_size"] = "CU"
                part1["beat_goal_suffix"] = "（拆镜上篇：蓄势微特写）"
                part2["action_physics_sec"] = round(act_sec * 0.52, 1)
                part2["narration"] = ""
                part2["keyframe_strategy"] = KeyframeStrategy.FIRST_AND_LAST_FRAMES
                part2["beat_goal_suffix"] = "（拆镜下篇：爆发落定）"
                result.extend([part1, part2])
                split_logs.append(
                    f"原单镜动作耗时 {act_sec}s > 5.0s 物理上限，已自动拆分为「CU蓄势镜({part1['action_physics_sec']}s) + 双关键帧爆发镜({part2['action_physics_sec']}s)」蒙太奇组。"
                )
            else:
                result.append(d)
        return result, split_logs

    @staticmethod
    def recalculate_timeline(shots: list[ShotSpec]) -> list[ShotSpec]:
        """Recompute cumulative timeline_in_sec / timeline_out_sec & EndFrame index cleanly."""
        cursor = 0.0
        for idx, shot in enumerate(shots, start=1):
            shot.shot_id = idx
            dur = shot.duration_budget.final_duration_sec
            frames = max(24, int(round(dur * 24)))
            shot.duration_budget.total_frames_24fps = frames
            shot.duration_budget.trim_out_frame = min(120, shot.duration_budget.trim_in_frame + frames - 1)
            shot.six_w_one_h.timeline_in_sec = round(cursor, 2)
            cursor = round(cursor + dur, 2)
            shot.six_w_one_h.timeline_out_sec = cursor
            shot.end_frame.frame_index = frames
            shot.end_frame.timestamp_sec = dur
        return shots

    async def build_storyboard(
        self,
        project_id: str,
        topic: str,
        charter: DirectorCharterAndLedger,
        strategy: StoryStrategyBlueprint,
        shot_count_hint: Optional[int] = None,
    ) -> list[ShotSpec]:
        await self.emit(
            project_id,
            "PLANNING_SCRIPT",
            "正在按五段心跳波形解算每镜科学时长、构建 Who/What/When/Where/Which/Why/How 七维矩阵与 24fps 首中尾关键帧…",
        )

        seeds = parse_topic_seeds(topic, charter.style_preset)
        prop_id = strategy.chekhov_props[0].prop_id if strategy.chekhov_props else "prop_chekhov_01"
        prop_name = strategy.chekhov_props[0].prop_name if strategy.chekhov_props else seeds["prop_main"][0]
        acc_name = seeds["acc_left"][0]
        lines_by_beat = {ln.beat_index: ln for ln in strategy.subtext_dialogue_list}

        # Crafted 6-shot heartbeat pacing curve (Hook -> Setup -> Escalation -> Silence -> Climax -> Afterglow)
        # Note: Shot 5 is intentionally authored with 2.9s explosive action + FIRST_AND_LAST_FRAMES!
        base_drafts: list[dict[str, Any]] = [
            {
                "beat_phase": "hook",
                "shot_size": "ECU",
                "lens": "100mm f/2.0 微距定焦",
                "action_physics_sec": 1.5,
                "speaker_id": None,
                "narration": "",
                "silence_ms": 0,
                "compass": "south",
                "h_zone": "center",
                "depth": "foreground",
                "elev": "low_angle_15",
                "view_angle": BodyViewAngle.THREE_QUARTER_FRONT,
                "co_chars": ["char_hero"],
                "prop_state": {prop_id: "carried"},
                "chekhov_ref": prop_id,
                "keyframe_strategy": KeyframeStrategy.SINGLE_START_FRAME,
                "cut_type": "cut_on_action",
                "speed_mode": "real_time_1x",
                "is_large_action": False,
                "goal": f"0.8s感官异变钩：{seeds['hero_name']}推门前结霜拇指已悄然顶开{prop_name}黄铜暗扣半寸寒芒",
                "what_event": f"带霜右手拇指压住{prop_name}紫竹柄铜扣推出2毫米剑锋寒光，伞尖冰珠震落",
                "env_react": "门缝灌入的暴风雪卷起细碎冰晶掠过镜头前景虚化散景",
                "focus_plan": f"死锁拇指指腹纹理与{prop_name}铜扣寒芒，背景风雪彻底奶油虚化",
                "motivation": "开篇第1帧建立『避寒旅人实则早有防备』的信息差钩子，0.8秒阻断划屏",
                "cam_how": "100mm微距15°微仰缓慢推进8厘米，冷青雪光勾勒金属高光边缘",
                "start_pose": f"Frame 01定格：右手四指稳托竹柄，大拇指刚刚抵紧黄铜机括尚未弹开，水珠悬于金属边缘",
                "mid_pose": "Frame 16 (0.67s)：拇指发力下压，铜扣弹开2毫米露出一线森冷剑光，冰珠脱离边缘坠落",
                "end_pose": "Frame 36：左手推向厚重松木门扇边缘，身体重心前倾准备跨入室内",
                "sync_cue": "第16帧：清脆金属机括『咔哒』轻响穿透风声",
            },
            {
                "beat_phase": "setup",
                "shot_size": "MLS",
                "lens": "35mm f/1.8 人文广角",
                "action_physics_sec": 3.2,
                "speaker_id": "char_rival",
                "narration": lines_by_beat.get(2).surface_line if 2 in lines_by_beat else "风雪封山，姑娘快喝口热汤。",
                "subtext": lines_by_beat.get(2).subtext_intent if 2 in lines_by_beat else "",
                "silence_ms": 300,
                "compass": "north",
                "h_zone": "right_third",
                "depth": "midground",
                "elev": "eye_level",
                "view_angle": BodyViewAngle.THREE_QUARTER_FRONT,
                "co_chars": ["char_rival", "char_hero"],
                "prop_state": {prop_id: "carried"},
                "chekhov_ref": None,
                "keyframe_strategy": KeyframeStrategy.SINGLE_START_FRAME,
                "cut_type": "eyeline_match_cut",
                "speed_mode": "real_time_1x",
                "is_large_action": False,
                "goal": f"建立三维空间方位与双人同框试探张力：{seeds['rival_name']}左前景递汤，{seeds['hero_name']}右中景踏雪入堂",
                "what_event": f"{seeds['hero_name']}肩披残雪踏上室内地台，{seeds['rival_name']}在左侧柜台双手捧粗陶热汤迎上，抹布下暗压铁尺",
                "env_react": "东侧雕花窗暖橘油灯与门外冷蓝风雪在木地板交汇，热汤白雾袅袅上升",
                "focus_plan": f"前1.2s实焦于左前景热汤碗沿，第1.3s平滑拉焦(Rack Focus)至右侧{seeds['hero_name']}冷冽双眼",
                "motivation": "交代北墙柜台/东窗油灯/南门入口空间拓扑，埋设掌柜热情假象下的伏击站位",
                "cam_how": "35mm斯坦尼康极慢速横移右摇，严格维持180度对峙轴线（掌柜居左朝右、侠女居右朝左）",
                "start_pose": f"Frame 01定格：{seeds['rival_name']}居左三分位侧身捧碗微笑，{seeds['hero_name']}居右三分位刚收步站定，肩头积雪未化",
                "mid_pose": f"Frame 42 (1.75s)：拉焦完成，{seeds['hero_name']}视线未看汤碗，反而微垂扫向柜台下方掌柜的靴尖",
                "end_pose": "Frame 82：侠女右手看似随意搭向肩后伞柄系带，眼神定格于地面",
                "sync_cue": "第10帧：湿靴实踩老松木地台低沉吱呀声 + 汤碗白雾嘶嘶声",
            },
            {
                "beat_phase": "escalation",
                "shot_size": "CU",
                "lens": "85mm f/1.4 肖像浅景深",
                "action_physics_sec": 2.2,
                "speaker_id": "char_hero",
                "narration": lines_by_beat.get(3).surface_line if 3 in lines_by_beat else "掌柜的靴底，怎么没沾雪？",
                "subtext": lines_by_beat.get(3).subtext_intent if 3 in lines_by_beat else "",
                "silence_ms": 550,
                "compass": "east",
                "h_zone": "center",
                "depth": "midground",
                "elev": "eye_level",
                "view_angle": BodyViewAngle.BACK,
                "co_chars": ["char_hero"],
                "prop_state": {prop_id: "carried"},
                "chekhov_ref": prop_id,
                "keyframe_strategy": KeyframeStrategy.SINGLE_START_FRAME,
                "cut_type": "j_cut_lead",
                "speed_mode": "real_time_1x",
                "is_large_action": False,
                "goal": "正背面构图展现冰山克制感与潜台词点破伪装，同时展示背面束发与斜跨道具背带一致性",
                "what_event": f"镜头从正背面捕捉{seeds['hero_name']}挺拔背影与斜背的{prop_name}，她微微侧首半寸一语点破破绽",
                "env_react": "东窗冷风钻隙而入，吹拂后脑束发发梢向右轻扬",
                "focus_plan": "实焦锁紧后脑束发铜饰与斜跨皮质背带肌理，远景掌柜惊愕面容处于浅景深半虚化中",
                "motivation": "利用正背面视角把长句潜台词自然化（规避正脸机械口型），用反常细节瞬间撕开平静假象",
                "cam_how": "85mm过肩背拍极慢推进，东侧暖烛形成发丝金色轮廓光(Rim Light)",
                "start_pose": f"Frame 01定格：180°正背面站姿，双肩沉稳放松，后脑束发与背后斜跨{prop_name}清晰分明",
                "mid_pose": "Frame 34 (1.42s)：随潜台词吐出，头部向左侧微偏12°露出少许下颌侧影，气定神闲",
                "end_pose": "Frame 67：右手自后腰探上握住伞柄末端，进入临战预备",
                "sync_cue": "第28帧：皮革背带轻微绷紧摩擦声",
            },
            {
                "beat_phase": "escalation",
                "shot_size": "ECU",
                "lens": "100mm f/2.0 微距定焦",
                "action_physics_sec": 1.3,
                "speaker_id": None,
                "narration": "",
                "silence_ms": 0,
                "compass": "east",
                "h_zone": "left_third",
                "depth": "foreground",
                "elev": "eye_level",
                "view_angle": BodyViewAngle.SIDE_PROFILE,
                "co_chars": ["char_hero"],
                "prop_state": {prop_id: "active_held"},
                "chekhov_ref": prop_id,
                "keyframe_strategy": KeyframeStrategy.SINGLE_START_FRAME,
                "cut_type": "cut_on_action",
                "speed_mode": "slow_mo_0.5x",
                "is_large_action": False,
                "goal": f"暴风雨前的1.4秒极致死寂：{acc_name}无风急颤预警梁上破空杀机",
                "what_event": f"全场呼吸屏绝，侧颜耳畔的{acc_name}受暗器破空劲风激荡骤然高频轻颤，瞳孔倒映一点寒星",
                "env_react": "背景油灯火苗突然被无形气浪压平45°，一滴融雪悬在半空升格慢放",
                "focus_plan": f"极浅景深死锁左耳{acc_name}银丝纹理与眼角余光",
                "motivation": "执行『极静衬极动』铁律，在高潮爆发前抽空配乐压缩1.4秒窒息感",
                "cam_how": "三脚架死锁机位(Tripod Locked)配合0.5x升格慢镜，极致克制放大微颤细节",
                "start_pose": f"Frame 01定格：90°正侧面特写，{acc_name}垂直静悬，眼神冷静平视前方",
                "mid_pose": f"Frame 18 (0.75s)：无形劲风袭来，{acc_name}向后急扬30°剧烈震颤，发丝随之扬起",
                "end_pose": "Frame 34：瞳孔骤缩锁定左上方来袭寒芒，颈部肌肉瞬间绷紧启动旋身",
                "sync_cue": "第18帧：配乐彻底抽空(Music Drop)，唯有一声清越急促的银铃颤音",
            },
            {
                "beat_phase": "climax",
                "shot_size": "MS",
                "lens": "35mm f/2.0 电影定焦",
                "action_physics_sec": 2.8,
                "speaker_id": None,
                "narration": "",
                "silence_ms": 0,
                "compass": "north",
                "h_zone": "center",
                "depth": "midground",
                "elev": "low_angle_15",
                "view_angle": BodyViewAngle.THREE_QUARTER_FRONT,
                "co_chars": ["char_hero"],
                "prop_state": {prop_id: "active_held"},
                "chekhov_ref": prop_id,
                "keyframe_strategy": KeyframeStrategy.FIRST_AND_LAST_FRAMES,
                "cut_type": "cut_on_action",
                "speed_mode": "ramped_speed",
                "is_large_action": True,
                "goal": f"高潮爆发双关键帧锁死：{seeds['hero_name']}旋身自{prop_name}拔出细剑凌空劈落偷袭铁镖（契诃夫伏笔引爆）",
                "what_event": f"右脚实踏地面木板借力拧腰，右手拔出{prop_name}内藏三尺细剑向右上方斜撩，火星四溅劈飞暗器，空伞鞘向左下方脱手掷出",
                "env_react": "剑气激起地面雪沫与桌角酒碗震碎，暖橘火花与冷白剑光炸裂交织",
                "focus_plan": "景深覆盖人物上半身至右上方剑锋交击点，保持90°快门角凌厉边缘无糊脸",
                "motivation": "引爆契诃夫伏笔道具，采用首尾双关键帧锁定大跨度旋身拔剑起止姿态防止I2V融化",
                "cam_how": "15°低角度稳机位微顺摇（触发动静互补防糊片铁律，严禁剧烈乱晃）",
                "start_pose": f"Frame 01首帧定格(蓄势极值点)：重心沉于右支撑腿，躯干呈C型蓄力微拧，右手紧握胸前{prop_name}竹柄已拔出三寸寒刃，披风向左侧垂落与右臂完全分离",
                "mid_pose": "Frame 32 (1.33s 峰值Apex)：脊柱S型展开发力，细剑斜指右上方格飞暗器迸出金红火花，披风与长发逆向朝左后方大幅扬起",
                "end_pose": "Frame 67尾帧定格(收势平衡帧)：双脚前后弓步稳扎青石木地台，右手持直剑斜指右下方滴水不沾，空伞鞘落于左脚侧0.5米地面，眼神冷冽直视前方",
                "sync_cue": "第08帧剑刃出鞘龙吟声 + 第32帧金铁交鸣脆响与丹田短促吐气声",
            },
            {
                "beat_phase": "afterglow",
                "shot_size": "MCU",
                "lens": "50mm f/1.4 标准大师镜",
                "action_physics_sec": 2.9,
                "speaker_id": "char_hero",
                "narration": lines_by_beat.get(5).surface_line if 5 in lines_by_beat else "炭火太旺，留给梁上客吧。",
                "subtext": lines_by_beat.get(5).subtext_intent if 5 in lines_by_beat else "",
                "silence_ms": 420,
                "compass": "south",
                "h_zone": "left_third",
                "depth": "midground",
                "elev": "eye_level",
                "view_angle": BodyViewAngle.THREE_QUARTER_FRONT,
                "co_chars": ["char_hero"],
                "prop_state": {prop_id: "active_held"},
                "chekhov_ref": prop_id,
                "keyframe_strategy": KeyframeStrategy.SINGLE_START_FRAME,
                "cut_type": "graphic_match",
                "speed_mode": "real_time_1x",
                "is_large_action": False,
                "goal": "余韵留白与首尾闭环彩蛋：收剑归鞘踏雪出门，散落铜牌与首镜寒光形成高复播闭环",
                "what_event": f"{seeds['hero_name']}神色复归平静，细剑滑回拾起的{prop_name}竹鞘，侧身迈向风雪门外；背景模糊处{seeds['rival_name']}衣襟滑出半枚同源旧铜牌",
                "env_react": "室内摇曳烛火渐稳，门外漫天飞雪映出冷白留白光晕",
                "focus_plan": f"实焦于{seeds['hero_name']}微湿鬓角与重新扣合的黄铜暗扣（视觉图形匹配切回第1镜第1帧！）",
                "motivation": "情绪从紧绷爆发回归冷峻留白，首尾铜扣构图无缝衔接诱发二刷，并埋下同门悬念彩蛋",
                "cam_how": "50mm轨道缓慢后拉(Dolly-out)，冷白雪光逐渐包裹画面边缘",
                "start_pose": f"Frame 01定格：肩头带雪、鬓发微湿（继承前镜状态），右手持细剑正对竹鞘口准备归鞘，{acc_name}余颤渐止",
                "mid_pose": "Frame 40 (1.67s)：剑刃丝滑推入竹鞘，大拇指轻合黄铜暗扣",
                "end_pose": "Frame 77：黄铜暗扣特写落位与全片第1镜第1帧构图精准重合，转身融入风雪",
                "sync_cue": "第44帧：黄铜剑扣合拢清音，与第1镜第16帧首尾呼应",
            },
        ]

        if shot_count_hint and 3 <= shot_count_hint < len(base_drafts):
            # Preserve Hook (0), Setup (1), Climax (4), Afterglow (5) priority
            keep_indices = [0, 1, 4, 5][:shot_count_hint] if shot_count_hint <= 4 else list(range(shot_count_hint))
            base_drafts = [base_drafts[i] for i in sorted(keep_indices)]

        checked_drafts, split_logs = self.split_overlong_action_drafts(base_drafts)
        for slog in split_logs:
            await self.emit(project_id, "PLANNING_SCRIPT", slog, level="warn")

        shots: list[ShotSpec] = []
        cursor_sec = 0.0

        for idx, d in enumerate(checked_drafts, start=1):
            budget = self.calculate_duration_envelope(
                shot_size=d["shot_size"],
                action_physics_sec=d["action_physics_sec"],
                narration=d.get("narration", ""),
                chars_per_sec=3.8,
                silence_before_ms=d.get("silence_ms", 350),
            )
            in_sec = round(cursor_sec, 2)
            out_sec = round(cursor_sec + budget.final_duration_sec, 2)
            cursor_sec = out_sec
            total_f = budget.total_frames_24fps
            mid_f = max(8, total_f // 2)

            start_snap = FrameSnapshotSpec(
                frame_index=1,
                timestamp_sec=0.0,
                beat_label="start_keyframe",
                pose_and_expression=d["start_pose"],
                prop_and_cloth_state=(
                    f"随身道具状态={d['prop_state']}；服饰干燥/落雪按连续性账本实时同步，无动作重影"
                ),
                camera_and_focus_state=f"{d['shot_size']} · {d['lens']} · 起始焦平面锁定",
                sync_sound_cue="环境底噪无缝铺底",
            )
            mid_snap = FrameSnapshotSpec(
                frame_index=mid_f,
                timestamp_sec=round(mid_f / 24.0, 2),
                beat_label="apex_beat" if d.get("is_large_action") else "micro_beat",
                pose_and_expression=d["mid_pose"],
                prop_and_cloth_state="柔性配饰与衣摆随运动产生自然惯性偏移",
                camera_and_focus_state=d["focus_plan"],
                sync_sound_cue=d["sync_cue"],
            )
            end_snap = FrameSnapshotSpec(
                frame_index=total_f,
                timestamp_sec=budget.final_duration_sec,
                beat_label="end_keyframe",
                pose_and_expression=d["end_pose"],
                prop_and_cloth_state="动作尾势收稳，视线与持物姿态严格作为下一镜首帧基准",
                camera_and_focus_state=f"衔接方式：{d['cut_type']}，预留切出动量窗口",
                sync_sound_cue="",
            )

            matrix = ShotSixWOneHMatrix(
                primary_subject_id=d["co_chars"][-1] if len(d["co_chars"]) > 1 else d["co_chars"][0],
                co_present_character_ids=d["co_chars"],
                secondary_and_offscreen_who=(
                    f"双人同框分区：{seeds['rival_name']}居左前景 vs {seeds['hero_name']}居右中景"
                    if len(d["co_chars"]) > 1
                    else f"画外存在：{seeds['rival_name']}潜伏注视与暗处弓手气机"
                ),
                character_continuity_state="继承前镜风雪湿发、体温呼吸白雾与持物连续状态",
                prop_active_states=d["prop_state"],
                narrative_beat_goal=d["goal"] + d.get("beat_goal_suffix", ""),
                physical_action_and_prop_event=d["what_event"],
                environmental_chain_reaction=d["env_react"],
                chekhov_prop_featured=d.get("chekhov_ref"),
                story_time_node=f"风雪子夜 · 戏剧节拍[{d['beat_phase'].upper()}]",
                timeline_in_sec=in_sec,
                timeline_out_sec=out_sec,
                temporal_speed_mode=d["speed_mode"],
                scene_id="scene_main_01",
                camera_compass_facing=d["compass"],
                spatial_zone_and_ground=f"构图区域={d['h_zone']} / 景深={d['depth']} · 实踩{seeds['floor_desc']}",
                which_shot_size=d["shot_size"],
                which_lens_and_aperture=d["lens"],
                which_keyframe_strategy=d["keyframe_strategy"],
                which_focus_plane_and_shift=d["focus_plan"],
                which_cut_transition=d["cut_type"],
                dramatic_motivation=d["motivation"],
                camera_angle_and_movement=d["cam_how"],
                lighting_and_color_contrast="遵循01总导演跨幕色彩总谱色温与冷暖侧逆光塑形",
                natural_acting_subtext="克制去舞台化微表演：眼神先于头部3帧启动，呼吸随受力收放",
                narration_and_sound_design=d["sync_cue"],
            )

            blocking = SpatialBlockingSpec(
                horizontal_zone=d["h_zone"],
                depth_plane=d["depth"],
                camera_elevation=d["elev"],
                body_view_angle=d["view_angle"],
                eyeline_direction="screen_left_mid" if d["h_zone"] == "right_third" else "screen_right_mid",
                ground_contact_and_shadow=(
                    f"双脚靴底与{seeds['floor_desc']}透视地平线严密贴合，脚底投射浓重接触暗影(Contact Shadow)与融雪湿痕，零悬浮感"
                ),
                environment_interaction=d["env_react"],
            )

            pose = AntiClippingPoseSpec(
                is_large_action=bool(d.get("is_large_action", False)),
                frozen_moment_phase="anticipation" if d.get("is_large_action") else "natural_rest",
                center_of_gravity_support="重心垂线稳落于右支撑足足弓，脊柱呈自然力学C/S动态曲线",
                limb_prop_separation_rule=(
                    "右臂持械向画面右前方净空区延展，外披与长发受反向惯性向画面左后方扬起，手臂、剑身与宽袖之间保持清晰负空间间隙无重叠"
                    if d.get("is_large_action")
                    else "手臂与躯干外衣自然分离，手部交互点留有清晰轮廓边缘"
                ),
                hand_grip_topology=(
                    f"右手五指紧扣{prop_name}紫竹柄护手下方圆柱面，大拇指锁死侧面铜扣，严禁剑刃穿过手掌或手指粘连"
                ),
            )

            shots.append(
                ShotSpec(
                    shot_id=idx,
                    beat_phase=d["beat_phase"],
                    speaker_id=d.get("speaker_id"),
                    narration=d.get("narration", ""),
                    subtext_note=d.get("subtext", ""),
                    duration_budget=budget,
                    six_w_one_h=matrix,
                    start_frame=start_snap,
                    mid_beat_frames=[mid_snap],
                    end_frame=end_snap,
                    spatial_blocking=blocking,
                    anticlipping_pose=pose,
                )
            )

        durations_str = " / ".join(f"S{s.shot_id}:{s.duration_budget.final_duration_sec}s" for s in shots)
        await self.emit(
            project_id,
            "PLANNING_SCRIPT",
            f"帧级分镜台本构建完成：共 {len(shots)} 镜，心跳时长波形 [{durations_str}]，累计 {cursor_sec:.1f}s ({int(round(cursor_sec*24))}帧)。",
            level="success",
            details={"shot_count": len(shots), "total_duration_sec": cursor_sec},
        )
        return shots
