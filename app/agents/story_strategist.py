"""Agent 02: Senior Story Strategist & Dramaturg (StoryStrategistAgent)."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    ChekhovPropArc,
    DirectorCharterAndLedger,
    IcebergCharacterSoul,
    InformationAsymmetryMode,
    StoryStrategyBlueprint,
    SubtextLineSpec,
)
from app.providers.mock import parse_topic_seeds

# Explicit Anti-AI Cliché Blacklist enforced by AntiClicheAuditor
AI_CLICHE_BLACKLIST: tuple[str, ...] = (
    "命运的齿轮",
    "嘴角勾起",
    "三分凉薄",
    "三分讥诮",
    "今天就是你的死期",
    "不再隐忍",
    "宿命的纠葛",
    "眼神中闪过一丝",
    "既然如此那就别怪我",
    "空气仿佛凝固了一般",
    "邪魅一笑",
)


class StoryStrategistAgent(BaseStudioAgent):
    """02 高级剧作策划总监：高概念反差、信息差悬念链、冰山人物、反AI套话潜台词与契诃夫伏笔表."""

    agent_id = "agent_02_story"
    agent_name = "02 高级剧作策划总监"

    @classmethod
    def audit_and_purify_subtext(
        cls, lines: list[SubtextLineSpec]
    ) -> tuple[list[SubtextLineSpec], list[str], bool]:
        """Scan dialogue against cliché blacklist & >11-char verbosity, auto-polishing violations."""
        rewrites: list[str] = []
        purified: list[SubtextLineSpec] = []

        fallback_crisp_lines = [
            "今年关外的炭，贵了三成。",
            "你的靴底，没沾雪。",
            "这碗热汤，留给梁上客吧。",
            "风停了，铃还没停。",
        ]

        for idx, item in enumerate(lines):
            raw = item.surface_line.strip()
            hit_cliches = [c for c in AI_CLICHE_BLACKLIST if c in raw]
            # Strip punctuation count for pure Chinese word economy check (<= 11 chars excluding punctuation)
            core_chars = [ch for ch in raw if ch not in "，。？！…—、,.?! \"'“”‘’"]
            too_long = len(core_chars) > 11

            if hit_cliches or too_long:
                replacement = fallback_crisp_lines[idx % len(fallback_crisp_lines)]
                reason = (
                    f"命中禁用套话 {hit_cliches}"
                    if hit_cliches
                    else f"字面台词达 {len(core_chars)} 字超出11字惜字上限"
                )
                rewrites.append(f"Beat {item.beat_index}: 原句「{raw}」因{reason} → 精修为潜台词短句「{replacement}」")
                item = item.model_copy(update={"surface_line": replacement})
            purified.append(item)

        return purified, rewrites, True

    async def build_story_strategy(
        self,
        project_id: str,
        topic: str,
        charter: DirectorCharterAndLedger,
    ) -> StoryStrategyBlueprint:
        await self.emit(
            project_id,
            "PLANNING_SCRIPT",
            "正在提炼高概念认知反差母题、信息差微钩子接力链与契诃夫道具三幕伏笔表…",
        )

        seeds = parse_topic_seeds(topic, charter.style_preset)
        llm_data: dict[str, Any] = await self.llm.generate_json(
            system_prompt=(
                "你是顶级短片剧作策划总监。请围绕用户创意构建高概念反差、单一极致情绪货币、"
                "信息差操控模式、每3-5秒微钩子接力链、契诃夫之枪三幕回收与首尾闭环彩蛋。"
            ),
            user_prompt=f"创意主题：{topic}\n总时长目标：{charter.target_total_duration_sec}s\n视觉基调：{charter.visual_medium_lock}",
            context={"task": "story_strategy", "topic": topic, "style_preset": charter.style_preset},
        )

        hero = IcebergCharacterSoul(
            character_id="char_hero",
            name=seeds["hero_name"],
            archetype_and_role=seeds["hero_role"],
            outer_mask="风雪赶路冻得指尖泛白、低眉敛目进屋讨一碗热汤的孤身过客",
            hidden_agenda=f"早已识破店内暗桩布局，借{seeds['prop_main'][0]}引蛇出洞查清旧案",
            behavioral_tic=f"落座或对话前，右手拇指总会极轻地摩挲{seeds['prop_main'][0]}的铜扣边缘半寸",
            speech_fingerprint="冷冽短句，每句不超9字，惯用环境物象反问，从不直白放狠话",
            micro_arc_shift="从敛锋试探（猎物伪装）→ 听风辨位（掌控全局）→ 寒光破局后孤身踏雪离去（执棋人收网）",
        )
        rival = IcebergCharacterSoul(
            character_id="char_rival",
            name=seeds["rival_name"],
            archetype_and_role="表面迎来送往的守店东家 / 实为设伏截杀的暗桩头目",
            outer_mask="满脸堆笑擦拭碗沿、热络招呼添炭倒汤的厚道长者",
            hidden_agenda="拖住来客视线，等梁上弓手合围一击必杀",
            behavioral_tic="笑眼弯起时左太阳穴青筋微跳，擦桌抹布下始终压着半截铁尺",
            speech_fingerprint="市井熟稔客套话，句尾带试探性慢腔",
            micro_arc_shift="从胜券在握的假意寒暄 → 被一句话点破靴底无雪后的瞳孔骤缩 → 机关算尽反被夺势",
        )

        chekhov_prop = ChekhovPropArc(
            prop_id="prop_chekhov_01",
            prop_name=seeds["prop_main"][0],
            owner_character_id="char_hero",
            plant_beat=(
                f"【第一幕·前埋 Plant】开场极特写：{seeds['hero_name']}推门避寒时，"
                f"背负的{seeds['prop_main'][0]}伞尖滴落雪水，铜扣已悄然错开一线缝隙。"
            ),
            escalation_beat=(
                f"【中段·异变 Escalation】双人隔桌寒暄时，{seeds['hero_name']}将{seeds['prop_main'][0]}横搁桌沿，"
                f"伴随{seeds['acc_left'][0]}无风微颤，拇指无声压下机括簧片。"
            ),
            payoff_climax_beat=(
                f"【高潮·引爆 Payoff】死寂破局瞬间，{seeds['prop_main'][0]}柄中三尺细剑电射而出，"
                "精准钉住偷袭暗器并映亮对手惊骇瞳孔，完成核心信物回收。"
            ),
        )

        raw_lines = [
            SubtextLineSpec(
                beat_index=2,
                speaker_id="char_rival",
                speaker_name=rival.name,
                surface_line="风雪封山，姑娘快喝口热汤。",
                subtext_intent="试探对方深浅，诱导她双手捧碗松开随身兵器。",
                silence_before_ms=300,
            ),
            SubtextLineSpec(
                beat_index=3,
                speaker_id="char_hero",
                speaker_name=hero.name,
                surface_line="掌柜的靴底，怎么没沾雪？",
                subtext_intent="一剑封喉的心理摊牌：你刚从干燥屋梁暗格下来，根本不是守店人。",
                silence_before_ms=550,
            ),
            SubtextLineSpec(
                beat_index=5,
                speaker_id="char_hero",
                speaker_name=hero.name,
                surface_line="炭火太旺，留给梁上客吧。",
                subtext_intent="破局收势，点破暗处埋伏已废，潇洒震慑全场。",
                silence_before_ms=420,
            ),
        ]

        purified_lines, rewrites_log, passed = self.audit_and_purify_subtext(raw_lines)

        mode_raw = llm_data.get("asymmetry_mode", "anomaly_mystery")
        try:
            asym_mode = InformationAsymmetryMode(mode_raw)
        except ValueError:
            asym_mode = InformationAsymmetryMode.ANOMALY_MYSTERY

        blueprint = StoryStrategyBlueprint(
            story_synopsis=llm_data.get("story_synopsis", f"围绕「{topic}」构建高反差悬疑反杀短片。"),
            high_concept_irony=llm_data.get(
                "high_concept_irony",
                "看似误入黑店避寒的柔弱孤客（猎物假象），实为借风雪上门清理门户的听风密探（猎人真身）",
            ),
            single_emotional_currency=llm_data.get(
                "single_emotional_currency", "极静暗流压迫下的瞬时反杀爽感"
            ),
            asymmetry_mode=asym_mode,
            opening_0_8s_hook_design=llm_data.get(
                "opening_0_8s_hook_design",
                f"前0.8秒反常感官极特写：结霜指尖已将{seeds['prop_main'][0]}黄铜暗扣顶开半寸寒光。",
            ),
            micro_hook_relay_chain=llm_data.get(
                "micro_hook_relay_chain",
                [
                    "0.0s-1.6s [异常钩] 避寒旅人进门前为何已顶开兵器暗扣？",
                    "1.6s-5.0s [破绽钩] 热情掌柜靴底干爽无雪、抹布下暗藏铁尺。",
                    "5.0s-6.4s [死寂钩] 1.4秒暴风雨前凝固死寂，左耳银铃无风急颤。",
                    "6.4s-15.5s [反杀闭环钩] 一剑破暗器，散落铜牌揭开同门幕后悬念。",
                ],
            ),
            iceberg_characters=[hero, rival],
            chekhov_props=[chekhov_prop],
            subtext_dialogue_list=purified_lines,
            sensory_synesthesia_points=[
                "【冷热触觉对撞】滚烫粗陶汤碗腾起的白雾撞上冰冷黄铜剑锷瞬间凝成细密水珠",
                f"【听觉视觉化微颤】屋外暴风低频压迫与{seeds['acc_left'][0]}高频微颤形成生理紧绷感",
                "【痛感与阻力细节】拇指重压机括簧片时指腹泛白与金属清脆弹开的触感反馈",
            ],
            quiet_before_storm_beat=llm_data.get(
                "quiet_before_storm_beat",
                "高潮前一镜强制插入 1.4s 暴风雨前死寂：呼吸屏住、烛火静止，仅一滴雪水自伞尖悬垂欲落。",
            ),
            loop_and_easter_egg=llm_data.get(
                "loop_and_easter_egg",
                f"首尾闭环：尾镜摇曳烛火与首镜铜扣寒光同构衔接；彩蛋：{rival.name}衣领滑出半枚同门旧铜牌。",
            ),
            anti_cliche_audit_passed=passed,
            cliche_rewrites_log=rewrites_log,
        )

        await self.emit(
            project_id,
            "PLANNING_SCRIPT",
            f"剧作策划定稿：信息差模式={blueprint.asymmetry_mode.value}，绑定契诃夫伏笔道具「{chekhov_prop.prop_name}」，反套话潜台词洁癖校验通过。",
            level="success",
            details={
                "chekhov_prop_id": chekhov_prop.prop_id,
                "dialogue_count": len(blueprint.subtext_dialogue_list),
            },
        )
        return blueprint
