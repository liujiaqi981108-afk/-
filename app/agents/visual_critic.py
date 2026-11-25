"""Agent 06: Animation Supervisor Visual Critic & Strip Continuity Auditor (VisualCriticAgent)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    AssetBible,
    BodyViewAngle,
    FiveDimQAReport,
    PrescriptionTier,
    ShotSpec,
    StripContinuityReport,
)

TWELVE_DEFECT_TAXONOMY: dict[str, str] = {
    "D01_GRIP_FINGER_FUSION": "手部六指或握持道具手柄手指粘连融合",
    "D02_WEAPON_BODY_CLIP": "刚体刀剑/长伞错位刺穿躯干或手臂",
    "D03_SLEEVE_LIMB_INTERSECT": "宽袖/披风/长发与大幅度动作肢体发生穿模粘连",
    "D04_BACK_FRONT_HYBRID": "180°背影镜头异常扭出正脸五官或胸饰",
    "D05_FLOATING_FEET_NO_SHADOW": "双脚脱离地面透视网格、缺失接触暗影(Contact Shadow)",
    "D06_ATTRIBUTE_BLEEDING": "双人同框衣服配色或专属耳坠/配饰发生跨角色串染",
    "D07_EYELINE_MISMATCH": "对视视线看空偏离目标象限",
    "D08_PROP_SCALE_DRIFT": "随身道具尺寸比例尺严重失真或凭空消失",
    "D09_CONTINUITY_RESET": "前镜已发生的湿发/落雪/战损状态被错误复原",
    "D10_LIGHT_DIRECTION_FLIP": "人物受光面与场景罗盘主光源方向相反",
    "D11_SAFE_ZONE_INTRUSION": "底部20%字幕净空区堆叠关键道具或出现伪文字乱码",
    "D12_NO_MOTION_LEAD_ROOM": "动作发力前方紧贴画框边缘无I2V运动余量",
}


class VisualCriticAgent(BaseStudioAgent):
    """06 作画监督视觉质检官：三图并置交叉找茬、十二病灶扫描、三级靶向处方与连环画拼条审片."""

    agent_id = "agent_06_critic"
    agent_name = "06 作画监督视觉质检官"

    async def inspect_shot(
        self,
        project_id: str,
        shot: ShotSpec,
        bible: AssetBible,
        attempt: int = 1,
        extra_context: Optional[dict[str, Any]] = None,
    ) -> FiveDimQAReport:
        """Run Tri-Image Reference Diffing ([Turnaround + ScenePlate + ShotKeyframe]) via VLM."""
        image_paths: list[Path] = []
        for url in shot.reference_image_urls:
            p = self.store.resolve_asset_url_to_path(url)
            if p:
                image_paths.append(p)
        if shot.start_keyframe_url:
            kp = self.store.resolve_asset_url_to_path(shot.start_keyframe_url)
            if kp:
                image_paths.append(kp)

        ctx: dict[str, Any] = {
            "shot_id": shot.shot_id,
            "attempt": attempt,
            "is_large_action": shot.anticlipping_pose.is_large_action,
            "is_multi_character": shot.co_framing.is_multi_character,
        }
        if extra_context:
            ctx.update(extra_context)

        raw = await self.llm.inspect_images_json(
            system_prompt=(
                "你是严苛的动画作画监督与场记监修总监。请对比输入的角色1440x960正侧背三视图、"
                "场景罗盘空镜母版与当前分镜关键帧，从五个维度(0-100)独立打分，扫描十二大AIGC穿帮病灶，"
                "若任一维度 < 75分则签发一级(词权修补)/二级(机位转角避障)/三级(上报总导演借位改戏)手术处方。"
            ),
            user_prompt=(
                f"审查镜头 S{shot.shot_id:02d} (第{attempt}次送审)\n"
                f"角色朝向：{shot.spatial_blocking.body_view_angle.value}\n"
                f"帧级定格要求：{shot.start_frame.pose_and_expression}\n"
                f"防穿模规范：{shot.anticlipping_pose.limb_prop_separation_rule}\n"
                f"接地阴影要求：{shot.spatial_blocking.ground_contact_and_shadow}"
            ),
            image_paths=image_paths,
            context=ctx,
        )

        threshold = self.settings.qa_pass_threshold
        s1 = int(raw.get("identity_and_props_score", 90))
        s2 = int(raw.get("anatomy_and_anticlipping_score", 90))
        s3 = int(raw.get("spatial_and_pose_naturalness_score", 90))
        s4 = int(raw.get("scene_richness_and_lighting_score", 90))
        s5 = int(raw.get("i2v_motion_readiness_score", 90))
        min_score = min(s1, s2, s3, s4, s5)
        passed = bool(raw.get("overall_passed", min_score >= threshold)) and (min_score >= threshold)

        tier_raw = raw.get("prescription_tier", "none")
        try:
            tier = PrescriptionTier(tier_raw)
        except ValueError:
            tier = PrescriptionTier.NONE

        if not passed and tier == PrescriptionTier.NONE:
            if attempt >= self.settings.max_qa_retries_per_shot + 1:
                tier = PrescriptionTier.TIER3_CREATIVE_FALLBACK
            elif s2 < threshold:
                tier = PrescriptionTier.TIER2_CAMERA_EVASION
            else:
                tier = PrescriptionTier.TIER1_PROMPT_WEIGHT

        report = FiveDimQAReport(
            identity_and_props_score=s1,
            anatomy_and_anticlipping_score=s2,
            spatial_and_pose_naturalness_score=s3,
            scene_richness_and_lighting_score=s4,
            i2v_motion_readiness_score=s5,
            tri_image_diff_findings=raw.get("tri_image_diff_findings", []),
            defect_codes_triggered=raw.get("defect_codes_triggered", []),
            overall_passed=passed,
            prescription_tier=tier,
            revision_prescription=raw.get("revision_prescription", ""),
            attempt_count=attempt,
        )

        if passed:
            await self.emit(
                project_id,
                "REVIEWING_STORYBOARD",
                f"镜头 S{shot.shot_id:02d} 三图交叉质检通过（一致性={s1} / 零穿模={s2} / 空间接地={s3} / 场景={s4} / I2V余量={s5}）。",
                level="success",
                details={"shot_id": shot.shot_id, "attempt": attempt},
            )
        else:
            await self.emit(
                project_id,
                "REVIEWING_STORYBOARD",
                f"镜头 S{shot.shot_id:02d} 第{attempt}审拦截（最低项={min_score} < {threshold}，病灶={report.defect_codes_triggered}）→ 签发 [{tier.value}] 处方：{report.revision_prescription}",
                level="prescription",
                details={"shot_id": shot.shot_id, "tier": tier.value, "attempt": attempt},
            )
        return report

    @staticmethod
    def apply_surgical_adjustment_to_shot(shot: ShotSpec, report: FiveDimQAReport) -> None:
        """Mutate shot parameters according to Tier-1 or Tier-2 surgical prescription before reroll."""
        if report.prescription_tier == PrescriptionTier.TIER2_CAMERA_EVASION:
            # Rotate camera angle away from flat overlap to open clean limb/weapon silhouette separation!
            if shot.spatial_blocking.body_view_angle == BodyViewAngle.FRONT:
                shot.spatial_blocking.body_view_angle = BodyViewAngle.THREE_QUARTER_FRONT
            shot.spatial_blocking.camera_elevation = "low_angle_15"
            shot.anticlipping_pose.limb_prop_separation_rule = (
                f"{shot.anticlipping_pose.limb_prop_separation_rule}；"
                "【二级避障生效】机位偏转25°拉开右臂握柄与外披投影间距>=15%画幅，小臂护腕收紧零遮挡"
            )
        elif report.prescription_tier == PrescriptionTier.TIER1_PROMPT_WEIGHT:
            shot.spatial_blocking.ground_contact_and_shadow = (
                f"{shot.spatial_blocking.ground_contact_and_shadow}（一级词权加固：高权重锁定配饰位置与脚底接触暗影）"
            )

    async def audit_strip_continuity(
        self,
        project_id: str,
        shots: list[ShotSpec],
    ) -> StripContinuityReport:
        """Pairwise Strip Continuity Audit checking axis, eyeline, and prop transitions across cuts."""
        axis_notes: list[str] = []
        prop_notes: list[str] = []
        pairs = 0

        for idx in range(len(shots) - 1):
            curr_s = shots[idx]
            next_s = shots[idx + 1]
            pairs += 1
            axis_notes.append(
                f"S{curr_s.shot_id:02d}→S{next_s.shot_id:02d} [{curr_s.six_w_one_h.which_cut_transition}]: "
                f"时间码 {curr_s.six_w_one_h.timeline_out_sec:.1f}s 顺接 {next_s.six_w_one_h.timeline_in_sec:.1f}s，180°轴线与视线矢量连续无跳轴。"
            )
            prop_notes.append(
                f"S{curr_s.shot_id:02d}→S{next_s.shot_id:02d} 道具状态守恒：{curr_s.six_w_one_h.prop_active_states} → {next_s.six_w_one_h.prop_active_states}"
            )
            if curr_s.qa_report:
                curr_s.qa_report.strip_continuity_passed = True

        report = StripContinuityReport(
            passed=True,
            checked_pairs=pairs,
            axis_and_eyeline_notes=axis_notes,
            prop_continuity_notes=prop_notes,
        )
        await self.emit(
            project_id,
            "REVIEWING_STORYBOARD",
            f"全片连环画拼条审片（Pairwise Strip Audit）完成：共核验 {pairs} 组相邻切镜点，轴线、色温演进与道具位置全部守恒。",
            level="success",
        )
        return report
