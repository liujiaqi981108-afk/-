"""Agent 04: Character 3-View, Props & 3D Scene Asset Director (ArtDirectorAgent)."""

from __future__ import annotations

import asyncio
import time
from typing import Optional

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    AccessorySpec,
    AspectRatio,
    AssetBible,
    BodyViewAngle,
    CarriedPropSpec,
    CharacterAssetCard,
    DirectorCharterAndLedger,
    SceneAssetCard,
    ShotSpec,
    StoryStrategyBlueprint,
)
from app.providers.base import ImageGenRequest
from app.providers.mock import parse_topic_seeds


class ArtDirectorAgent(BaseStudioAgent):
    """04 角色三视图与三维场景总监：五维角色档案+1440x960正侧背三视图+随身物双态卡+东南西北空镜母版."""

    agent_id = "agent_04_art"
    agent_name = "04 角色与场景资产总监"

    @staticmethod
    def compile_turnaround_prompt(char: CharacterAssetCard, global_style: str) -> str:
        acc_desc = "; ".join(
            f"{a.name} locked at {a.wear_location} ({a.material_and_detail})"
            for a in char.accessories
        )
        prop_desc = "; ".join(
            f"{p.name} ({p.scale_reference}) — [Carried]: {p.carried_state_desc} | [Active Held]: {p.active_held_state_desc}"
            for p in char.carried_props
        )
        return (
            f"Character orthographic reference turnaround sheet, 1440x960 neutral studio slate grey background, "
            f"strict head-to-toe horizontal proportion guide lines (1.0H to 7.5H), three full-body views side-by-side: "
            f"[LEFT: 0-degree full front view] [CENTER: 90-degree side profile view] [RIGHT: 180-degree full back view], "
            f"plus inset callout boxes on right edge showing accessories and dual-state prop details. "
            f"Style: {global_style}. Character: {char.name} ({char.role_type}). "
            f"Anatomy & Bone Structure: {char.anatomy_and_silhouette}. "
            f"Hair Front: {char.hair_front} | Hair Side: {char.hair_side} | Hair Back: {char.hair_back}. "
            f"Layered Wardrobe: {char.wardrobe_layered}. Signature Palette: {', '.join(char.signature_colors)}. "
            f"Fixed Accessories: {acc_desc}. Carried Props: {prop_desc}."
        )

    @staticmethod
    def compile_scene_plate_prompt(scene: SceneAssetCard, global_style: str) -> str:
        compass_str = " | ".join(f"{k.upper()}: {v}" for k, v in scene.compass_topology.items())
        return (
            f"Empty master architectural environment concept plate, STRICTLY NO PEOPLE, NO CHARACTERS. "
            f"Style: {global_style}. Location: {scene.name}. "
            f"Fixed 3D Compass Topology: {compass_str}. "
            f"Foreground Depth Framing: {scene.foreground_layer}. "
            f"Midground Interactive Set Dressing: {scene.midground_interactive_props}. "
            f"Deep Background Lived-In Worldbuilding: {scene.background_world_details}. "
            f"Floor Surface: {scene.floor_material_and_acoustic}. "
            f"Master Lighting & Atmosphere: {scene.lighting_and_atmosphere}."
        )

    async def build_assets(
        self,
        project_id: str,
        topic: str,
        aspect_ratio: AspectRatio,
        charter: DirectorCharterAndLedger,
        strategy: StoryStrategyBlueprint,
        shots: list[ShotSpec],
    ) -> AssetBible:
        await self.emit(
            project_id,
            "BUILDING_ASSETS",
            "正在构建角色五维视觉档案（正/侧/背发型、分层服饰、左右锁定配饰、契诃夫随身物双态卡）与三维罗盘场景拓扑…",
        )

        seeds = parse_topic_seeds(topic, charter.style_preset)
        chekhov = strategy.chekhov_props[0] if strategy.chekhov_props else None
        prop_id = chekhov.prop_id if chekhov else "prop_chekhov_01"
        prop_name = chekhov.prop_name if chekhov else seeds["prop_main"][0]

        hero_card = CharacterAssetCard(
            character_id="char_hero",
            name=seeds["hero_name"],
            role_type=seeds["hero_role"],
            anatomy_and_silhouette=(
                "23岁清冷矫健女性，身高169cm（标准7.5头身骨感匀称比例），平肩窄腰，下颌线利落，"
                "凤眼深黑瞳仁极亮，左眼尾下方2mm处有一颗极淡冷褐泪痣（严格锁定角色左侧面部）"
            ),
            hair_front="墨黑长发中分微偏左，两缕微湿碎发贴于左颧骨旁，露出饱满额头与冷峻眉骨",
            hair_side="耳前留一束齐下颌冷冽鬓发，清晰露出耳廓结构与左耳垂挂饰，后脑发束高扎呈流线倾角",
            hair_back="后脑以暗金螭纹窄发冠高束马尾，发尾垂至肩胛骨中段，发丝层次分明不散乱遮背",
            wardrobe_layered=(
                "【内层】炭黑高领贴身交领劲装（锁骨处密实保暖无多余裸露）；"
                "【中层】深绯暗红粗纺窄袖束腰长衣，袖口以皮革护腕严密收束紧贴小臂（专为大动作拔剑防穿模设计！）；"
                "【外层】玄黑防风毛领半身短披风（下摆止于腰际上方，衣摆两侧高开衩，运动时向后翻飞绝不缠绕双腿与右臂）；"
                "【下装与鞋靴】墨黑束口鹿皮长靴，靴头与靴筒下沿沾有细碎白雪与微湿水痕"
            ),
            signature_colors=seeds["palette_hero"],
            accessories=[
                AccessorySpec(
                    accessory_id="acc_hero_ear_01",
                    name=seeds["acc_left"][0],
                    wear_location=seeds["acc_left"][1],
                    visible_angles=[
                        BodyViewAngle.FRONT,
                        BodyViewAngle.THREE_QUARTER_FRONT,
                        BodyViewAngle.SIDE_PROFILE,
                    ],
                    material_and_detail=seeds["acc_left"][2],
                    is_flexible_pendulum=True,
                ),
                AccessorySpec(
                    accessory_id="acc_hero_wrist_02",
                    name=seeds["acc_right"][0],
                    wear_location=seeds["acc_right"][1],
                    visible_angles=[
                        BodyViewAngle.FRONT,
                        BodyViewAngle.THREE_QUARTER_FRONT,
                        BodyViewAngle.SIDE_PROFILE,
                    ],
                    material_and_detail=seeds["acc_right"][2],
                    is_flexible_pendulum=False,
                ),
                AccessorySpec(
                    accessory_id="acc_hero_hair_03",
                    name="暗金螭纹窄发冠与玄色束发带",
                    wear_location="hair_back_crown",
                    visible_angles=[
                        BodyViewAngle.SIDE_PROFILE,
                        BodyViewAngle.THREE_QUARTER_BACK,
                        BodyViewAngle.BACK,
                    ],
                    material_and_detail="哑光旧黄铜束冠配18cm玄黑麻质发带垂尾，背面视角核心识别锚点",
                    is_flexible_pendulum=True,
                ),
            ],
            carried_props=[
                CarriedPropSpec(
                    prop_id=prop_id,
                    name=prop_name,
                    is_chekhov_gun=True,
                    is_rigid_body=True,
                    scale_reference=seeds["prop_main"][1],
                    visual_detail="深紫老竹伞骨配桐油暗纹伞面，竹柄中段嵌一枚做旧六角黄铜机括暗扣，内藏笔直青霜细剑",
                    carried_state_desc=seeds["prop_main"][2],
                    active_held_state_desc=seeds["prop_main"][3],
                )
            ],
            negative_drift_tokens=[
                "blonde hair",
                "loose wide kimono sleeves",
                "hat or helmet",
                "earring on right ear",
                "modern sneakers",
                "bare shoulders",
            ],
        )
        hero_card.turnaround_prompt = self.compile_turnaround_prompt(hero_card, charter.visual_medium_lock)

        rival_card = CharacterAssetCard(
            character_id="char_rival",
            name=seeds["rival_name"],
            role_type="设伏暗桩头目（伪装掌柜）",
            anatomy_and_silhouette=(
                "48岁精悍微驼背男性，身高174cm，宽厚肩背藏练家子筋骨，方阔脸膛，右眉骨横贯一道寸许旧浅疤"
            ),
            hair_front="灰黑夹杂短发全部向后梳拢束进深青布巾，额纹深刻",
            hair_side="双鬓斑白修剪利落，耳廓厚实无耳饰",
            hair_back="深青粗布包头巾在脑后打死结，短发茬干净贴合后颈",
            wardrobe_layered=(
                "【内层】灰褐粗麻立领短衫；【中层】深铁青油布半旧掌柜围裙；"
                "【外层】暗墨色厚棉坎肩；【鞋靴】一双干爽无半点泥雪的厚底黑布快靴（关键叙事破绽！）"
            ),
            signature_colors=seeds["palette_rival"],
            accessories=[
                AccessorySpec(
                    accessory_id="acc_rival_thumb_01",
                    name="左手拇指暗青铁扳指",
                    wear_location="left_thumb",
                    visible_angles=[BodyViewAngle.FRONT, BodyViewAngle.THREE_QUARTER_FRONT, BodyViewAngle.SIDE_PROFILE],
                    material_and_detail="生铁磨砂宽戒面，内侧带暗器挂槽",
                    is_flexible_pendulum=False,
                ),
                AccessorySpec(
                    accessory_id="acc_rival_waist_02",
                    name="腰间半掩同门旧铜牌与账房算盘挂件",
                    wear_location="waist_right",
                    visible_angles=[BodyViewAngle.FRONT, BodyViewAngle.SIDE_PROFILE, BodyViewAngle.BACK],
                    material_and_detail="边缘磨损的半枚螭纹暗铜腰牌藏于围裙侧褶下（结尾彩蛋伏笔）",
                    is_flexible_pendulum=True,
                ),
            ],
            carried_props=[
                CarriedPropSpec(
                    prop_id="prop_rival_bowl_02",
                    name="粗陶热汤碗与压尺灰抹布",
                    is_chekhov_gun=False,
                    is_rigid_body=True,
                    scale_reference="碗口直径14cm粗粝黑釉陶碗，灰布长35cm下掩半截乌铁尺",
                    visual_detail="陶碗边缘有一处旧磕口，腾起浓白热雾",
                    carried_state_desc="灰抹布搭于左肩，乌铁尺藏于右腰围裙暗袋",
                    active_held_state_desc="双手托举粗陶碗递向前方，右手小指与无名指在灰布下死扣乌铁尺柄",
                )
            ],
            negative_drift_tokens=[
                "crimson red robe",
                "silver bell earring",
                "young boyish face",
                "snow on boots",
            ],
        )
        rival_card.turnaround_prompt = self.compile_turnaround_prompt(rival_card, charter.visual_medium_lock)

        scene_card = SceneAssetCard(
            scene_id="scene_main_01",
            name=seeds["scene_name"],
            compass_topology={
                "north": "主背景老榆木高柜台、酒坛木架与通往二楼暗廊的木梯（掌柜常驻方位）",
                "east": "半掩雕花支摘木窗与桌面黄铜防风油灯（全堂暖琥珀主侧光与冷风穿堂入口）",
                "south": "厚重包铁老松木双扇大门，门外暴风雪肆虐（侠女推门入堂方位）",
                "west": "斑驳夯土墙面悬挂旧蓑衣、风干草药与泛黄关防告示（剑影投射墙面）",
                "floor": seeds["floor_desc"],
            },
            foreground_layer="近景虚化垂落的粗麻门帘流苏、飘入室内的细碎雪粒与热汤氤氲白雾，营造呼吸景深",
            midground_interactive_props="包浆深沉的八仙榆木方桌、长条板凳、黄铜油灯、粗陶酒坛与柜台算盘（高度82cm真实人体工学交互尺度）",
            background_world_details="熏黑房梁垂挂旧灯笼、墙角堆放柴禾竹篓、墙壁刀痕与陈年烟火油渍，杜绝AI空旷塑料感",
            floor_material_and_acoustic=seeds["floor_desc"] + "（湿皮靴踩踏发低沉实木闷响与融水轻溅声）",
            lighting_and_atmosphere=(
                "冷暖双色温戏剧对撞：南门与东窗缝隙灌入 6800K 冷铁青风雪背光，"
                "中景桌面黄铜油灯与炭盆散发 2900K 暖琥珀火光，空气中弥漫丁达尔微尘与寒气白雾"
            ),
            palette_hex=seeds["scene_palette"],
        )
        scene_card.master_plate_prompt = self.compile_scene_plate_prompt(scene_card, charter.visual_medium_lock)

        bible = AssetBible(
            global_style_tokens=charter.visual_medium_lock,
            global_negative_tokens=charter.global_negative_mandate,
            characters=[hero_card, rival_card],
            scenes=[scene_card],
        )

        # Render Character 1440x960 3-View Turnaround Sheets + Scene Master Plate concurrently
        pdir = self.store.project_dir(project_id)
        plate_w, plate_h = (720, 1280) if aspect_ratio == AspectRatio.VERTICAL_9_16 else (1280, 720)
        ts = int(time.time() * 1000)

        async def _gen_char(c: CharacterAssetCard) -> None:
            out_file = pdir / "turnarounds" / f"{c.character_id}.png"
            await self.img.generate_image(
                ImageGenRequest(
                    kind="character_turnaround",
                    prompt=c.turnaround_prompt,
                    negative_prompt=", ".join(c.negative_drift_tokens) + ", " + bible.global_negative_tokens,
                    width=1440,
                    height=960,
                    output_path=out_file,
                    metadata=c.model_dump(mode="json"),
                )
            )
            c.turnaround_image_url = f"{self.store.asset_url(project_id, 'turnarounds', out_file.name)}?v={ts}"

        async def _gen_scene(s: SceneAssetCard) -> None:
            out_file = pdir / "scenes" / f"{s.scene_id}.png"
            await self.img.generate_image(
                ImageGenRequest(
                    kind="scene_plate",
                    prompt=s.master_plate_prompt,
                    negative_prompt="people, human figure, crowd, character, " + bible.global_negative_tokens,
                    width=plate_w,
                    height=plate_h,
                    output_path=out_file,
                    metadata=s.model_dump(mode="json"),
                )
            )
            s.master_plate_image_url = f"{self.store.asset_url(project_id, 'scenes', out_file.name)}?v={ts}"

        await asyncio.gather(
            *[_gen_char(c) for c in bible.characters],
            *[_gen_scene(s) for s in bible.scenes],
        )

        await self.emit(
            project_id,
            "BUILDING_ASSETS",
            f"视觉资产先行锁定完成：已生成 {len(bible.characters)} 张 1440x960 正/侧/背角色三视图设定卡与 {len(bible.scenes)} 张无人场景空镜母版图。",
            level="success",
            details={
                "characters": [c.name for c in bible.characters],
                "scenes": [s.name for s in bible.scenes],
            },
        )
        return bible

    async def regenerate_character_turnaround(
        self,
        project_id: str,
        bible: AssetBible,
        character_id: str,
        custom_note: str = "",
    ) -> CharacterAssetCard:
        target: Optional[CharacterAssetCard] = next(
            (c for c in bible.characters if c.character_id == character_id), None
        )
        if not target:
            raise ValueError(f"Character not found: {character_id}")

        if custom_note.strip():
            target.wardrobe_layered = f"{target.wardrobe_layered}（总监精修补充：{custom_note.strip()}）"
        target.turnaround_prompt = self.compile_turnaround_prompt(target, bible.global_style_tokens)

        out_file = self.store.project_dir(project_id) / "turnarounds" / f"{target.character_id}.png"
        await self.img.generate_image(
            ImageGenRequest(
                kind="character_turnaround",
                prompt=target.turnaround_prompt,
                negative_prompt=", ".join(target.negative_drift_tokens) + ", " + bible.global_negative_tokens,
                width=1440,
                height=960,
                output_path=out_file,
                metadata=target.model_dump(mode="json"),
            )
        )
        target.turnaround_image_url = (
            f"{self.store.asset_url(project_id, 'turnarounds', out_file.name)}?v={int(time.time() * 1000)}"
        )
        await self.emit(
            project_id,
            "BUILDING_ASSETS",
            f"已单独重抽角色「{target.name}」的 1440x960 正/侧/背标准三视图设定卡。",
            level="success",
        )
        return target

    async def regenerate_scene_plate(
        self,
        project_id: str,
        bible: AssetBible,
        aspect_ratio: AspectRatio,
        scene_id: str,
        custom_note: str = "",
    ) -> SceneAssetCard:
        target: Optional[SceneAssetCard] = next(
            (s for s in bible.scenes if s.scene_id == scene_id), None
        )
        if not target:
            raise ValueError(f"Scene not found: {scene_id}")

        if custom_note.strip():
            target.midground_interactive_props = (
                f"{target.midground_interactive_props}（总监精修补充：{custom_note.strip()}）"
            )
        target.master_plate_prompt = self.compile_scene_plate_prompt(target, bible.global_style_tokens)

        plate_w, plate_h = (720, 1280) if aspect_ratio == AspectRatio.VERTICAL_9_16 else (1280, 720)
        out_file = self.store.project_dir(project_id) / "scenes" / f"{target.scene_id}.png"
        await self.img.generate_image(
            ImageGenRequest(
                kind="scene_plate",
                prompt=target.master_plate_prompt,
                negative_prompt="people, human figure, character, " + bible.global_negative_tokens,
                width=plate_w,
                height=plate_h,
                output_path=out_file,
                metadata=target.model_dump(mode="json"),
            )
        )
        target.master_plate_image_url = (
            f"{self.store.asset_url(project_id, 'scenes', out_file.name)}?v={int(time.time() * 1000)}"
        )
        await self.emit(
            project_id,
            "BUILDING_ASSETS",
            f"已单独重抽主场景「{target.name}」的三维罗盘空镜母版图。",
            level="success",
        )
        return target
