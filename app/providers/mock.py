"""Zero-Key Studio Mock LLM/VLM & Procedural Concept/Storyboard Image Engine."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any, Optional
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.providers.base import BaseImageProvider, BaseLLMProvider, ImageGenRequest

FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]
FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_REGULAR_CANDIDATES
    for fp in candidates + FONT_REGULAR_CANDIDATES:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str, fallback: tuple[int, int, int] = (210, 95, 65)) -> tuple[int, int, int]:
    h = (hex_color or "").strip().lstrip("#")
    if len(h) == 6:
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            pass
    return fallback


def _blend(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def parse_topic_seeds(topic: str, style_preset: str = "") -> dict[str, Any]:
    """Extract or synthesize rich thematic entities from any user prompt."""
    t = topic.strip()
    is_cyber = any(k in t for k in ("赛博", "霓虹", "机甲", "未来", "科幻", "机械", "黑客", "废土"))
    is_modern = any(k in t for k in ("咖啡", "地铁", "都市", "便利店", "写字楼", "现代", "天台", "侦探"))

    if is_cyber:
        hero_name = "零音 (Ling Yin)"
        rival_name = "铁叔 (Old Kuro)"
        if "少女" in t or "机械师" in t:
            hero_role = "霓虹暗巷义体钟表修缮师"
        else:
            hero_role = "赛博潜行信使"
        acc_left = ("左耳骨单枚钛银脉冲耳夹", "left_ear", "哑光钛银配微蓝呼吸灯点，长2.8cm")
        acc_right = ("右手腕绝缘编织铜芯护腕", "right_wrist", "深棕芳纶织带缠绕三圈嵌黄铜接口")
        prop_main = ("改装黄铜机械怀表终端", "直径6.5cm厚重旧黄铜表壳，连35cm暗银锁链", "斜挂于左侧工装腰袢，表链垂入左袋", "右手掌托表底、拇指按压顶部棘轮弹开全息星盘")
        scene_name = "霓虹雨夜地下修械铺"
        palette_hero = ["#D9534F", "#2B3440", "#E6A23C"]
        palette_rival = ["#3A4A58", "#1C2228", "#6C8EA4"]
        scene_palette = ["#0F1722", "#1F3A4D", "#E08E45"]
        floor_desc = "带机油反光与雨水积洼的防滑菱纹钢板地面"
    elif is_modern:
        hero_name = "林知夏"
        rival_name = "陈默（深夜店长）"
        hero_role = "深夜独立调查摄影师"
        acc_left = ("左耳细圈暗金耳扣", "left_ear", "直径1.6cm哑光古金圆环，随转头微闪")
        acc_right = ("颈间黑色胶片相机皮质窄挂绳", "neck_front", "磨砂植鞣牛皮配黄铜三角环")
        prop_main = ("银黑旁轴复古胶片相机", "宽13.5cm金属机身配35mm定焦铜圈镜头", "斜挎于左肩收在驼色风衣左腰侧", "双手举至右眼平视取景，右食指半按快门钮")
        scene_name = "梅雨夜街角深夜旧书咖啡馆"
        palette_hero = ["#C87D55", "#252930", "#E3C598"]
        palette_rival = ["#2F3E46", "#1B2024", "#84A98C"]
        scene_palette = ["#161B20", "#2C3840", "#D99B52"]
        floor_desc = "磨出温润包浆与门口雨渍的深胡桃木鱼骨拼花地板"
    else:
        # Default / Wuxia / Oriental Cinema / Fantasy rich adaptation
        hero_name = "沈惊鸿" if "侠" in t or "红衣" in t or "剑" in t else "苏晚照"
        rival_name = "陆掌柜（暗桩统领）"
        hero_role = "独行边关听风密探侠女"
        acc_left = (
            "左耳暗银六棱风铃耳坠" if "银铃" in t or "耳坠" in t else "左耳暗银流苏坠耳饰",
            "left_ear",
            "旧银镂空小铃配2.5cm红丝坠穗，遇微风即轻颤",
        )
        acc_right = ("右手腕三圈朱砂旧麻绳护腕", "right_wrist", "褪色暗红细麻绳配一枚铜钱压扣")
        prop_main = (
            "藏锋竹骨油纸伞" if "伞" in t else "乌木鞘听雪细剑",
            "全长88cm约为身高一半，紫竹柄长18cm嵌黄铜机括暗扣",
            "黑布革带自左肩斜跨胸前背负于右后背，伞尖朝下滴落雪水",
            "右手五指紧握竹柄黄铜护手下方，拇指顶开铜扣拔出三尺青霜细剑",
        )
        scene_name = "暴风雪夜关外孤灯古驿站" if ("雪" in t or "驿站" in t) else "风夜残灯古客栈堂前"
        palette_hero = ["#B8332A", "#1E2229", "#D9A441"]
        palette_rival = ["#2C353D", "#15181C", "#7A8B99"]
        scene_palette = ["#131921", "#243240", "#DF923E"]
        floor_desc = "嵌有积雪融水与岁月裂纹的青灰条石拼老松木地台"

    return {
        "topic": t,
        "style_preset": style_preset or "35mm 冷峻电影胶片写实",
        "is_cyber": is_cyber,
        "is_modern": is_modern,
        "hero_name": hero_name,
        "rival_name": rival_name,
        "hero_role": hero_role,
        "acc_left": acc_left,
        "acc_right": acc_right,
        "prop_main": prop_main,
        "scene_name": scene_name,
        "palette_hero": palette_hero,
        "palette_rival": palette_rival,
        "scene_palette": scene_palette,
        "floor_desc": floor_desc,
    }


class MockLLMProvider(BaseLLMProvider):
    """Context-aware local studio brain enabling deterministic zero-key full runs."""

    vendor_name = "mock"

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        ctx = context or {}
        task = ctx.get("task", "")
        seeds = parse_topic_seeds(ctx.get("topic", user_prompt), ctx.get("style_preset", ""))

        if task == "director_charter":
            return {
                "title": f"《{seeds['scene_name'][:6]}·惊蛰》",
                "visual_medium_lock": (
                    f"{seeds['style_preset']} · ARRI Alexa Mini LF 配合 Cooke Anamorphic 变形宽银幕镜头肌理，"
                    "真实光学浅景深、皮肤毛孔与织物经纬可见，严禁3D游戏塑料感与平涂插画风"
                ),
                "global_negative_mandate": (
                    "3d render, plastic skin, anime cel shading, extra fingers, weapon clipping through body, "
                    "floating feet without shadow, watermark, text overlay, split screen border"
                ),
            }

        if task == "story_strategy":
            return {
                "story_synopsis": (
                    f"围绕「{seeds['topic']}」展开：外表风尘仆仆入店避寒的{seeds['hero_name']}，"
                    f"实则借{seeds['prop_main'][0]}试探潜伏在{seeds['scene_name']}内的{seeds['rival_name']}，"
                    "在三秒死寂对峙后以信物破局反杀。"
                ),
                "high_concept_irony": (
                    f"看似冻僵求宿的孤身旅人（猎物表象），实为早算准屋中埋伏、上门收网的执棋者（猎人真相）"
                ),
                "single_emotional_currency": "极静压迫感下的智商与武力双重瞬时反杀爽感",
                "asymmetry_mode": "anomaly_mystery",
                "opening_0_8s_hook_design": (
                    f"0.8秒极特写反常细节：门外风雪呼啸，{seeds['hero_name']}{seeds['acc_left'][0]}结满白霜，"
                    f"但搭在{seeds['prop_main'][0]}铜扣上的大拇指却稳如磐石已推开半寸寒芒。"
                ),
                "micro_hook_relay_chain": [
                    f"[0.0s-1.8s 异常钩] 进屋避寒客手指为何已悄然顶开{seeds['prop_main'][0]}机括？",
                    f"[1.8s-5.2s 破绽钩] {seeds['rival_name']}热情迎客，袖口阴影里却紧绷着发力青筋与干爽无雪的靴尖。",
                    f"[5.2s-9.5s 死寂钩] 烛火无风骤偏，{seeds['acc_left'][0]}突然急颤预警暗处杀机！",
                    f"[9.5s-16.0s 反转钩] 寒光破鞘一气呵成，结尾一枚散落腰牌留下更大幕后悬念。",
                ],
                "chekhov_prop_name": seeds["prop_main"][0],
                "quiet_before_storm_beat": (
                    "高潮爆发前预留 1.3 秒极致死寂：所有动作凝固，仅一滴融雪自伞尖慢速坠向地面青石，未碎之际寒光骤起。"
                ),
                "loop_and_easter_egg": (
                    f"首尾闭环：尾帧摇曳复归平静的烛火与开篇第一帧门缝冷光构图重合；"
                    f"彩蛋：{seeds['rival_name']}滑落的衣襟内露出一角与主角同源的旧铜纹印记。"
                ),
            }

        return {"status": "ok", "seeds": seeds}

    async def inspect_images_json(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: list[Path],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Deterministic cross-image VLM QA simulation with realistic self-healing."""
        ctx = context or {}
        attempt = int(ctx.get("attempt", 1))
        is_large_action = bool(ctx.get("is_large_action", False))
        force_fail_tier = ctx.get("force_fail_tier")

        # Verify files actually exist and have non-zero size
        missing = [str(p) for p in image_paths if not p.exists() or p.stat().st_size == 0]
        if missing:
            return {
                "identity_and_props_score": 40,
                "anatomy_and_anticlipping_score": 40,
                "spatial_and_pose_naturalness_score": 40,
                "scene_richness_and_lighting_score": 40,
                "i2v_motion_readiness_score": 40,
                "tri_image_diff_findings": [f"图像文件缺失: {missing}"],
                "defect_codes_triggered": ["FILE_MISSING"],
                "overall_passed": False,
                "prescription_tier": "tier1_prompt_weight",
                "revision_prescription": "重新触发图像渲染管线。",
            }

        if force_fail_tier == "tier3":
            return {
                "identity_and_props_score": 84,
                "anatomy_and_anticlipping_score": 58,
                "spatial_and_pose_naturalness_score": 66,
                "scene_richness_and_lighting_score": 86,
                "i2v_motion_readiness_score": 62,
                "tri_image_diff_findings": [
                    "对比角色三视图：正面全身急速挥斩导致右小臂、刀锷与宽袖三者投影完全重叠粘连"
                ],
                "defect_codes_triggered": ["D02_WEAPON_BODY_CLIP", "D03_SLEEVE_LIMB_INTERSECT"],
                "overall_passed": False,
                "prescription_tier": "tier3_creative_fallback",
                "revision_prescription": "连续正面全身拼刀发生重叠穿模，建议上报01总导演启动『寒光映瞳极特写+墙面剑影借位蒙太奇』熔断改戏。",
            }

        # Demonstrate real self-healing on first attempt of high-difficulty large action shot
        if is_large_action and attempt == 1 and not ctx.get("skip_first_action_heal", False):
            return {
                "identity_and_props_score": 88,
                "anatomy_and_anticlipping_score": 68,
                "spatial_and_pose_naturalness_score": 76,
                "scene_richness_and_lighting_score": 89,
                "i2v_motion_readiness_score": 74,
                "tri_image_diff_findings": [
                    "三图并置核查：角色左耳配饰与场景罗盘东窗受光准确，但大动作正前机位下宽袖边缘与持握柄手指轻微粘连重叠（评分68 < 75阈值）"
                ],
                "defect_codes_triggered": ["D01_GRIP_FINGER_FUSION", "D03_SLEEVE_LIMB_INTERSECT"],
                "overall_passed": False,
                "prescription_tier": "tier2_camera_evasion",
                "revision_prescription": (
                    "【二级转角避障手术】将摄影机水平偏转 25° 切换为 3/4 前侧微仰机位，强制拉开右手握柄与躯干外披投影间距 ≥15% 画幅，并显式束紧右腕护腕露出完整五指抓握拓扑。"
                ),
            }

        return {
            "identity_and_props_score": 93,
            "anatomy_and_anticlipping_score": 91 if is_large_action else 95,
            "spatial_and_pose_naturalness_score": 92,
            "scene_richness_and_lighting_score": 94,
            "i2v_motion_readiness_score": 90,
            "tri_image_diff_findings": [
                "三图交叉核验通过：发型分缝、固定左右配饰与随身物比例尺与1440x960三视图严格一致",
                "场景透视核验通过：双脚实踩地面具备清晰接触暗影（Contact Shadow），前中后三层景深与主光源吻合",
                "运动余量核验通过：动作发力前方预留充足 Lead Room，底部20%字幕安全区净空无遮挡",
            ],
            "defect_codes_triggered": [],
            "overall_passed": True,
            "prescription_tier": "none",
            "revision_prescription": "",
        }


class MockImageProvider(BaseImageProvider):
    """Procedural Studio Concept Sheet, Scene Master Plate & Storyboard Renderer."""

    vendor_name = "mock"

    async def generate_image(self, req: ImageGenRequest) -> Path:
        req.output_path.parent.mkdir(parents=True, exist_ok=True)
        if req.kind == "character_turnaround":
            img = self._render_character_turnaround(req)
        elif req.kind == "scene_plate":
            img = self._render_scene_plate(req)
        else:
            img = self._render_storyboard_keyframe(req)
        img.save(req.output_path, format="PNG")
        return req.output_path

    def _render_character_turnaround(self, req: ImageGenRequest) -> Image.Image:
        w, h = req.width or 1440, req.height or 960
        meta = req.metadata or {}
        img = Image.new("RGB", (w, h), (26, 29, 34))
        draw = ImageDraw.Draw(img)

        f_title = _load_font(28, bold=True)
        f_sub = _load_font(18, bold=True)
        f_body = _load_font(15, bold=False)
        f_small = _load_font(13, bold=False)

        colors = meta.get("signature_colors") or ["#B8332A", "#1E2229", "#D9A441"]
        c_primary = _hex_to_rgb(colors[0], (184, 51, 42))
        c_secondary = _hex_to_rgb(colors[1] if len(colors) > 1 else "#1E2229", (34, 39, 46))
        c_accent = _hex_to_rgb(colors[2] if len(colors) > 2 else "#D9A441", (217, 164, 65))

        # Header Studio Slate
        draw.rectangle([0, 0, w, 74], fill=(18, 20, 24))
        draw.line([0, 74, w, 74], fill=c_accent, width=2)
        char_name = meta.get("name", "核心角色")
        role_type = meta.get("role_type", "主角设定")
        draw.text((32, 18), f"CHARACTER ORTHOGRAPHIC BIBLE · {char_name}", fill=(242, 239, 233), font=f_title)
        draw.text((32, 50), f"五维角色资产卡 · 正/侧/背标准正交三视图 + 左右配饰锁 + 随身道具双态拆解  |  {role_type}", fill=(165, 172, 182), font=f_small)

        # Left 66% Area: Orthographic 3-View Studio Grid (Front 0° / Side 90° / Back 180°)
        sheet_box = [28, 96, 950, h - 28]
        draw.rounded_rectangle(sheet_box, radius=10, fill=(35, 39, 46), outline=(58, 64, 74), width=2)

        top_head_y = 175
        feet_ground_y = h - 92
        total_fig_h = feet_ground_y - top_head_y

        # 1H - 7.5H Head-Proportion Horizontal Alignment Guides
        for step in range(8):
            gy = int(top_head_y + (total_fig_h / 7.5) * step)
            draw.line([48, gy, 930, gy], fill=(48, 53, 62), width=1)
            label = "0.0H 顶线" if step == 0 else f"{step}.0H"
            draw.text((54, gy - 16), label, fill=(112, 120, 132), font=f_small)
        # Ground baseline
        draw.line([48, feet_ground_y, 930, feet_ground_y], fill=(125, 134, 148), width=2)
        draw.text((54, feet_ground_y + 6), "7.5H 透视接地面 (ORTHOGRAPHIC GROUND LOCK)", fill=c_accent, font=f_small)

        views = [
            ("FRONT 0° 正面全身", 235, "front"),
            ("PROFILE 90° 侧面全身", 515, "side"),
            ("BACK 180° 背面全身", 795, "back"),
        ]
        for label, cx, vmode in views:
            draw.text((cx - 78, 118), label, fill=(230, 226, 218), font=f_sub)
            # Contact shadow ellipse
            draw.ellipse([cx - 56, feet_ground_y - 9, cx + 56, feet_ground_y + 11], fill=(20, 22, 26))
            self._draw_stylized_figure(
                draw,
                cx=cx,
                top_y=top_head_y,
                bottom_y=feet_ground_y,
                view=vmode,
                c_primary=c_primary,
                c_secondary=c_secondary,
                c_accent=c_accent,
                prop_active=(vmode == "front"),
            )

        # Callout pins on turnaround
        acc_list = meta.get("accessories") or []
        if acc_list:
            first_acc = acc_list[0].get("name", "左耳标志配饰")
            # Viewer's right of front head = character's left ear!
            ear_x, ear_y = 235 + 24, top_head_y + 42
            draw.ellipse([ear_x - 5, ear_y - 5, ear_x + 5, ear_y + 5], fill=c_accent)
            draw.line([ear_x + 5, ear_y, ear_x + 68, ear_y - 24], fill=c_accent, width=2)
            draw.text((ear_x + 72, ear_y - 34), f"★ {first_acc} (角色左耳)", fill=c_accent, font=f_small)

        # Right 32% Area: Swatches + Accessories + Dual-State Carried Props Cards
        rx0, rx1 = 974, w - 28
        # Color Triad Card
        draw.rounded_rectangle([rx0, 96, rx1, 215], radius=10, fill=(31, 35, 42), outline=(58, 64, 74), width=1)
        draw.text((rx0 + 18, 110), "SIGNATURE COLOR TRIAD · 标志三色锁", fill=(235, 232, 225), font=f_sub)
        sw_w = (rx1 - rx0 - 56) // 3
        for idx, hex_code in enumerate(colors[:3]):
            sx = rx0 + 18 + idx * (sw_w + 10)
            rgb = _hex_to_rgb(hex_code)
            draw.rounded_rectangle([sx, 145, sx + sw_w, 186], radius=6, fill=rgb, outline=(90, 96, 108))
            draw.text((sx + 8, 190), hex_code.upper(), fill=(175, 182, 192), font=f_small)

        # Accessories Card
        draw.rounded_rectangle([rx0, 232, rx1, 515], radius=10, fill=(31, 35, 42), outline=(58, 64, 74), width=1)
        draw.text((rx0 + 18, 248), "FIXED ACCESSORIES · 左右部位锁定配饰", fill=c_accent, font=f_sub)
        ay = 284
        for acc in acc_list[:3]:
            aname = acc.get("name", "配饰")
            aloc = acc.get("wear_location", "left_ear")
            adet = acc.get("material_and_detail", "")
            draw.rounded_rectangle([rx0 + 16, ay, rx1 - 16, ay + 68], radius=6, fill=(24, 27, 33), outline=(48, 54, 64))
            draw.text((rx0 + 26, ay + 8), f"[{aloc.upper()}] {aname}", fill=(238, 235, 228), font=f_body)
            draw.text((rx0 + 26, ay + 34), adet[:26] + ("…" if len(adet) > 26 else ""), fill=(155, 162, 174), font=f_small)
            ay += 76

        # Carried Props Dual-State Card (Chekhov's Gun Highlight)
        draw.rounded_rectangle([rx0, 532, rx1, h - 28], radius=10, fill=(31, 35, 42), outline=c_accent, width=2)
        draw.text((rx0 + 18, 548), "CHEKHOV PROP DUAL-STATE · 随身物双态卡", fill=c_accent, font=f_sub)
        props = meta.get("carried_props") or []
        if props:
            p0 = props[0]
            draw.text((rx0 + 18, 582), f"◆ {p0.get('name', '核心随身道具')}", fill=(242, 239, 233), font=f_body)
            draw.text((rx0 + 18, 608), f"比例尺: {p0.get('scale_reference', '')[:27]}", fill=(170, 178, 190), font=f_small)
            # Carried box
            draw.rounded_rectangle([rx0 + 16, 638, rx1 - 16, 765], radius=6, fill=(23, 26, 32), outline=(55, 62, 72))
            draw.text((rx0 + 26, 648), "① 常驻挂载态 (CARRIED / HOLSTERED)", fill=(130, 200, 185), font=f_small)
            self._draw_wrapped_text(draw, p0.get("carried_state_desc", ""), rx0 + 26, 672, rx1 - rx0 - 52, f_small, (198, 204, 214), max_lines=4)
            # Active held box
            draw.rounded_rectangle([rx0 + 16, 778, rx1 - 16, h - 44], radius=6, fill=(23, 26, 32), outline=(95, 72, 42))
            draw.text((rx0 + 26, 788), "② 手持激活态 (ACTIVE / HELD TOPOLOGY)", fill=c_accent, font=f_small)
            self._draw_wrapped_text(draw, p0.get("active_held_state_desc", ""), rx0 + 26, 812, rx1 - rx0 - 52, f_small, (215, 210, 200), max_lines=4)

        return img

    def _render_scene_plate(self, req: ImageGenRequest) -> Image.Image:
        w, h = req.width or 1280, req.height or 720
        meta = req.metadata or {}
        pal = meta.get("palette_hex") or ["#131921", "#243240", "#DF923E"]
        c_dark = _hex_to_rgb(pal[0], (19, 25, 33))
        c_mid = _hex_to_rgb(pal[1] if len(pal) > 1 else "#243240", (36, 50, 64))
        c_warm = _hex_to_rgb(pal[2] if len(pal) > 2 else "#DF923E", (223, 146, 62))

        img = Image.new("RGB", (w, h), c_dark)
        draw = ImageDraw.Draw(img, "RGBA")
        horizon_y = int(h * 0.56)

        # Atmospheric vertical gradient
        for y in range(h):
            if y < horizon_y:
                col = _blend(c_dark, c_mid, y / max(1, horizon_y))
            else:
                col = _blend(_blend(c_mid, (28, 26, 24), 0.45), (14, 16, 20), (y - horizon_y) / max(1, h - horizon_y))
            draw.line([0, y, w, y], fill=col)

        # Volumetric key light rays from East window (right-top)
        for i in range(6):
            spread = 90 + i * 55
            poly = [
                (int(w * 0.84), int(h * 0.12)),
                (int(w * 0.25) + spread, horizon_y + int(h * 0.28)),
                (int(w * 0.12) + spread, horizon_y + int(h * 0.28)),
            ]
            draw.polygon(poly, fill=(c_warm[0], c_warm[1], c_warm[2], 22))

        # Perspective Floor Grid (Grounded Horizon)
        vp_x = int(w * 0.5)
        for k in range(-9, 10):
            end_x = vp_x + k * int(w * 0.12)
            draw.line([vp_x, horizon_y, end_x, h], fill=(255, 255, 255, 26), width=1)
        for r in range(1, 8):
            ry = horizon_y + int(((r / 7.0) ** 1.65) * (h - horizon_y))
            draw.line([0, ry, w, ry], fill=(255, 255, 255, 24), width=1)

        # Deep Background Architectural Silhouettes (North wall / beams / eaves)
        draw.rectangle([int(w * 0.08), int(h * 0.16), int(w * 0.12), horizon_y + 30], fill=(16, 20, 26, 220))
        draw.rectangle([int(w * 0.86), int(h * 0.14), int(w * 0.91), horizon_y + 40], fill=(16, 20, 26, 220))
        # Glowing East Window Lattice & Warm Lantern
        win_box = [int(w * 0.72), int(h * 0.22), int(w * 0.84), int(h * 0.48)]
        draw.rectangle(win_box, fill=(c_warm[0], c_warm[1], c_warm[2], 75), outline=(c_warm[0], c_warm[1], c_warm[2], 180), width=2)
        # Midground Interactive Table / Counter Anchor
        tbl_y = int(horizon_y + (h - horizon_y) * 0.24)
        draw.rectangle([int(w * 0.26), tbl_y, int(w * 0.64), tbl_y + 18], fill=(56, 42, 32, 235), outline=(92, 70, 52, 220))
        draw.rectangle([int(w * 0.30), tbl_y + 18, int(w * 0.33), tbl_y + 92], fill=(42, 31, 24, 235))
        draw.rectangle([int(w * 0.57), tbl_y + 18, int(w * 0.60), tbl_y + 92], fill=(42, 31, 24, 235))
        # Warm oil lamp on midground table
        lamp_x = int(w * 0.55)
        draw.ellipse([lamp_x - 28, tbl_y - 46, lamp_x + 28, tbl_y + 8], fill=(c_warm[0], c_warm[1], c_warm[2], 65))
        draw.ellipse([lamp_x - 7, tbl_y - 22, lamp_x + 7, tbl_y - 4], fill=(255, 224, 150, 245))

        # Foreground Bokeh Framing Pillars (Left & Right edges)
        draw.rectangle([0, 0, int(w * 0.045), h], fill=(8, 10, 14, 215))
        draw.rectangle([int(w * 0.955), 0, w, h], fill=(8, 10, 14, 215))

        # Top Studio Slate & Compass Rose Overlay
        f_bold = _load_font(20, bold=True)
        f_small = _load_font(13, bold=False)
        draw.rectangle([0, 0, w, 58], fill=(12, 14, 18, 215))
        sname = meta.get("name", "主场景空镜母版")
        draw.text((22, 10), f"MASTER SCENE PLATE (NO ACTORS) · {sname}", fill=(240, 236, 228), font=f_bold)
        draw.text((22, 36), "三维空间罗盘拓扑锁定 · 前景遮挡层 + 中景交互陈设区 + 远景世界观纵深 + 主光源体积光", fill=c_warm, font=f_small)

        # Compass Topology Card bottom-left
        compass = meta.get("compass_topology") or {}
        cw_box = [20, h - 138, min(w - 20, 520), h - 18]
        draw.rounded_rectangle(cw_box, radius=8, fill=(14, 17, 22, 210), outline=(72, 82, 96, 180), width=1)
        cy = h - 128
        for k_dir, label in (("north", "北 N"), ("east", "东 E"), ("south", "南 S"), ("west", "西 W")):
            val = compass.get(k_dir, "")
            if val:
                draw.text((32, cy), f"{label}: {val[:28]}", fill=(196, 204, 216), font=f_small)
                cy += 26

        return img

    def _render_storyboard_keyframe(self, req: ImageGenRequest) -> Image.Image:
        w, h = req.width or 720, req.height or 1280
        meta = req.metadata or {}
        shot_id = meta.get("shot_id", 1)
        frame_tag = meta.get("frame_tag", "START FRAME 01")
        is_end_frame = "END" in frame_tag.upper()
        kelvin_hex = meta.get("act_colors") or ["#18222D", "#D98A3C"]
        c_bg_top = _hex_to_rgb(kelvin_hex[0], (22, 30, 40))
        c_accent = _hex_to_rgb(kelvin_hex[-1], (224, 159, 62))

        img = Image.new("RGB", (w, h), c_bg_top)
        draw = ImageDraw.Draw(img, "RGBA")

        elev = meta.get("camera_elevation", "eye_level")
        horizon_ratio = 0.62 if elev == "low_angle_15" else (0.42 if elev == "high_angle_20" else 0.52)
        horizon_y = int(h * horizon_ratio)
        safe_zone_y = int(h * 0.80)

        # Gradient sky/wall & floor
        for y in range(h):
            if y < horizon_y:
                col = _blend(c_bg_top, _blend(c_bg_top, c_accent, 0.22), y / max(1, horizon_y))
            else:
                col = _blend((32, 34, 38), (14, 15, 18), (y - horizon_y) / max(1, h - horizon_y))
            draw.line([0, y, w, y], fill=col)

        # Perspective Ground Grid
        vp_x = int(w * (0.56 if is_end_frame else 0.48))
        for k in range(-7, 8):
            draw.line([vp_x, horizon_y, vp_x + k * int(w * 0.16), h], fill=(255, 255, 255, 22), width=1)
        for r in range(1, 7):
            ry = horizon_y + int(((r / 6.0) ** 1.6) * (safe_zone_y - horizon_y))
            draw.line([0, ry, w, ry], fill=(255, 255, 255, 20), width=1)

        # Ambient key light cone
        draw.polygon(
            [(int(w * 0.88), int(h * 0.08)), (int(w * 0.18), safe_zone_y), (int(w * 0.68), safe_zone_y)],
            fill=(c_accent[0], c_accent[1], c_accent[2], 28),
        )

        # Midground Architecture / Props
        draw.rectangle([int(w * 0.10), int(h * 0.14), int(w * 0.16), horizon_y + 40], fill=(18, 21, 26, 200))
        draw.rectangle([int(w * 0.76), int(h * 0.18), int(w * 0.90), int(h * 0.40)], fill=(c_accent[0], c_accent[1], c_accent[2], 58), outline=(c_accent[0], c_accent[1], c_accent[2], 145), width=2)

        # Character Placement (Single vs Multi-Character Left/Right Partitioning)
        is_multi = bool(meta.get("is_multi_character", False))
        shot_size = meta.get("shot_size", "MS")
        hero_colors = meta.get("hero_colors") or ["#B8332A", "#1E2229", "#D9A441"]
        rival_colors = meta.get("rival_colors") or ["#2C353D", "#15181C", "#7A8B99"]
        view_raw = meta.get("body_view_angle", "3_4_front")
        vmode = "back" if "back" in view_raw else ("side" if "side" in view_raw else "front")
        prop_active = bool(meta.get("prop_active", False)) or is_end_frame

        zone_map = {"left_third": 0.33, "center": 0.50, "right_third": 0.67}
        cx_ratio = zone_map.get(meta.get("horizontal_zone", "center"), 0.50)
        if is_end_frame:
            cx_ratio = min(0.72, cx_ratio + 0.06)

        if is_multi:
            # Hard Left / Right Spatial Partitioning Visualized!
            lx = int(w * 0.29)
            rx = int(w * 0.71)
            foot_y = int(safe_zone_y - h * 0.04)
            fig_h = int(h * 0.44)
            # Subtle partition divider guide
            draw.line([w // 2, int(h * 0.18), w // 2, foot_y], fill=(255, 255, 255, 28), width=1)
            # Contact shadows
            draw.ellipse([lx - 52, foot_y - 10, lx + 52, foot_y + 12], fill=(8, 9, 12, 230))
            draw.ellipse([rx - 52, foot_y - 10, rx + 52, foot_y + 12], fill=(8, 9, 12, 230))
            self._draw_stylized_figure(
                draw, lx, foot_y - fig_h, foot_y, "side",
                _hex_to_rgb(rival_colors[0]), _hex_to_rgb(rival_colors[1]), _hex_to_rgb(rival_colors[2]),
                prop_active=False,
            )
            self._draw_stylized_figure(
                draw, rx, foot_y - fig_h, foot_y, "front",
                _hex_to_rgb(hero_colors[0]), _hex_to_rgb(hero_colors[1]), _hex_to_rgb(hero_colors[2]),
                prop_active=prop_active,
            )
            # Mutual Eyeline Lock Vector
            eye_y = foot_y - int(fig_h * 0.88)
            draw.line([lx + 24, eye_y, rx - 24, eye_y], fill=(72, 210, 190, 175), width=2)
        else:
            cx = int(w * cx_ratio)
            if shot_size in ("ECU", "CU"):
                # Close-up framing: larger upper silhouette
                foot_y = int(h * 0.96)
                fig_h = int(h * 0.72)
            elif shot_size in ("MCU", "MS"):
                foot_y = int(safe_zone_y + h * 0.04)
                fig_h = int(h * 0.54)
            else:
                foot_y = int(safe_zone_y - h * 0.03)
                fig_h = int(h * 0.44)

            if foot_y <= safe_zone_y + 8:
                # Grounded Contact Shadow!
                draw.ellipse([cx - 64, foot_y - 11, cx + 64, foot_y + 13], fill=(6, 8, 10, 235))

            self._draw_stylized_figure(
                draw,
                cx=cx,
                top_y=foot_y - fig_h,
                bottom_y=foot_y,
                view=vmode,
                c_primary=_hex_to_rgb(hero_colors[0]),
                c_secondary=_hex_to_rgb(hero_colors[1]),
                c_accent=_hex_to_rgb(hero_colors[2]),
                prop_active=prop_active,
                is_large_action=bool(meta.get("is_large_action", False)),
            )

        # Atmospheric snow / dust particles
        seed_int = int(hashlib.md5(f"{shot_id}_{frame_tag}".encode()).hexdigest()[:8], 16)
        for p_idx in range(28):
            px = (seed_int * (p_idx + 3) * 37) % w
            py = (seed_int * (p_idx + 7) * 53) % safe_zone_y
            r = 2 if p_idx % 4 == 0 else 1
            draw.ellipse([px - r, py - r, px + r, py + r], fill=(240, 245, 255, 115))

        # Foreground depth vignette frame
        draw.rectangle([0, 0, int(w * 0.03), h], fill=(6, 8, 11, 165))
        draw.rectangle([int(w * 0.97), 0, w, h], fill=(6, 8, 11, 165))

        # Protected Bottom 20% Safe Zone Subtle Guide & Slate Header
        f_bold = _load_font(17, bold=True)
        f_small = _load_font(12, bold=False)
        draw.rectangle([0, 0, w, 54], fill=(10, 12, 16, 215))
        lens = meta.get("lens", "50mm")
        draw.text(
            (16, 8),
            f"SHOT {shot_id:02d} · {frame_tag} · {shot_size} ({lens})",
            fill=(242, 239, 232),
            font=f_bold,
        )
        draw.text(
            (16, 32),
            f"朝向: {view_raw}  |  锚点垫图: {len(req.reference_images)} refs  |  透视接地阴影已锁定",
            fill=c_accent,
            font=f_small,
        )

        # Safe zone subtle dashed boundary at 80% height
        for sx in range(16, w - 16, 24):
            draw.line([sx, safe_zone_y, sx + 12, safe_zone_y], fill=(224, 159, 62, 85), width=1)
        draw.text((18, safe_zone_y + 8), "SAFE ZONE (底部20%字幕净空保护区)", fill=(165, 172, 184, 150), font=f_small)

        narration = meta.get("narration", "")
        if narration:
            f_sub = _load_font(18, bold=True)
            tw = int(len(narration) * 18)
            bx0 = max(20, (w - tw) // 2 - 16)
            bx1 = min(w - 20, (w + tw) // 2 + 16)
            sy = int(h * 0.84)
            draw.rounded_rectangle([bx0, sy, bx1, sy + 36], radius=6, fill=(10, 12, 15, 190))
            draw.text((bx0 + 14, sy + 7), narration[:22], fill=(246, 243, 236), font=f_sub)

        return img.convert("RGB")

    def _draw_stylized_figure(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        top_y: int,
        bottom_y: int,
        view: str,
        c_primary: tuple[int, int, int],
        c_secondary: tuple[int, int, int],
        c_accent: tuple[int, int, int],
        prop_active: bool = False,
        is_large_action: bool = False,
    ) -> None:
        h = max(120, bottom_y - top_y)
        head_r = max(12, int(h * 0.066))
        head_cy = top_y + head_r
        neck_y = head_cy + head_r
        shoulder_y = top_y + int(h * 0.17)
        waist_y = top_y + int(h * 0.42)
        hem_y = top_y + int(h * 0.76)

        # Cloak / Outer cape swept away on large action (Anti-clipping separation!)
        cape_shift = -36 if is_large_action else (-14 if view == "side" else 0)
        cape_poly = [
            (cx - int(h * 0.10), shoulder_y),
            (cx + int(h * 0.10), shoulder_y),
            (cx + int(h * 0.16) + cape_shift, hem_y + 18),
            (cx - int(h * 0.18) + cape_shift, hem_y + 18),
        ]
        draw.polygon(cape_poly, fill=c_secondary if view == "back" else _blend(c_primary, (20, 20, 24), 0.32))

        # Legs / Boots firmly planted on bottom_y
        leg_spread = int(h * (0.085 if is_large_action else 0.045))
        if view == "side":
            leg_spread = int(h * 0.035)
        draw.line([cx - leg_spread, waist_y, cx - leg_spread - 4, bottom_y], fill=c_secondary, width=max(6, int(h * 0.036)))
        draw.line([cx + leg_spread, waist_y, cx + leg_spread + 4, bottom_y], fill=c_secondary, width=max(6, int(h * 0.036)))

        # Layered Tunic / Torso
        sh_half = int(h * (0.065 if view == "side" else 0.105))
        waist_half = int(h * (0.05 if view == "side" else 0.07))
        torso_poly = [
            (cx - sh_half, shoulder_y),
            (cx + sh_half, shoulder_y),
            (cx + waist_half, waist_y),
            (cx + int(sh_half * 1.15), hem_y),
            (cx - int(sh_half * 1.15), hem_y),
            (cx - waist_half, waist_y),
        ]
        draw.polygon(torso_poly, fill=c_primary, outline=_blend(c_primary, (255, 255, 255), 0.18))
        # Sash / Belt accent
        draw.rectangle([cx - waist_half - 2, waist_y - 5, cx + waist_half + 2, waist_y + 6], fill=c_accent)

        # Head & View-Specific Hair / Facial Direction (Front vs Side vs Back!)
        if view == "back":
            # Back of head covered completely by dark hair & ribbon — NEVER draw front facial features!
            draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=(24, 26, 32))
            draw.polygon(
                [(cx - head_r + 2, head_cy), (cx + head_r - 2, head_cy), (cx + 10 + cape_shift // 2, waist_y - 12), (cx - 10 + cape_shift // 2, waist_y - 12)],
                fill=(18, 20, 25),
            )
            draw.ellipse([cx - 5, head_cy - 4, cx + 5, head_cy + 6], fill=c_accent)
            # Diagonal strap across back
            draw.line([cx - sh_half + 4, shoulder_y + 2, cx + waist_half, waist_y], fill=(92, 68, 44), width=4)
        elif view == "side":
            draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=(226, 198, 176))
            # Hair covering back half of profile
            draw.pieslice([cx - head_r - 2, head_cy - head_r - 2, cx + head_r + 2, head_cy + head_r + 2], start=110, end=295, fill=(22, 24, 30))
            # Eye looking right
            draw.ellipse([cx + head_r // 2 - 2, head_cy - 3, cx + head_r // 2 + 2, head_cy + 1], fill=(25, 25, 28))
        else:
            # Front / 3_4 Front
            draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=(228, 200, 178))
            draw.pieslice([cx - head_r - 2, head_cy - head_r - 3, cx + head_r + 2, head_cy + head_r], start=185, end=355, fill=(22, 24, 30))
            # Eyes
            ey_w = max(3, head_r // 3)
            draw.ellipse([cx - ey_w - 2, head_cy - 2, cx - ey_w + 2, head_cy + 2], fill=(24, 24, 28))
            draw.ellipse([cx + ey_w - 2, head_cy - 2, cx + ey_w + 2, head_cy + 2], fill=(24, 24, 28))
            # Left ear accessory (on viewer's right side of head!)
            draw.line([cx + head_r + 1, head_cy + 3, cx + head_r + 3, head_cy + 15], fill=c_accent, width=2)
            draw.ellipse([cx + head_r, head_cy + 14, cx + head_r + 6, head_cy + 20], fill=c_accent)

        # Prop Dual-State Rendering (Carried on back vs Held extended in clean negative space!)
        if prop_active and view != "back":
            hand_x = cx + sh_half + int(h * (0.14 if is_large_action else 0.08))
            hand_y = shoulder_y + int(h * (0.04 if is_large_action else 0.14))
            # Arm clearly separated from cape/torso
            draw.line([cx + sh_half - 2, shoulder_y + 6, hand_x, hand_y], fill=c_primary, width=max(5, int(h * 0.028)))
            # Wristband on right wrist
            draw.ellipse([hand_x - 5, hand_y - 5, hand_x + 5, hand_y + 5], fill=c_accent)
            # Rigid straight prop/blade extending outward in clean negative space (zero torso clipping!)
            tip_x = hand_x + int(h * 0.24)
            tip_y = hand_y - int(h * (0.22 if is_large_action else 0.12))
            draw.line([hand_x - 10, hand_y + 8, tip_x, tip_y], fill=(215, 224, 235), width=3)
            draw.line([hand_x - 6, hand_y - 5, hand_x + 6, hand_y + 7], fill=c_accent, width=3)
        else:
            # Holstered diagonal prop behind shoulder
            draw.line(
                [cx - sh_half - 8, top_y + int(h * 0.08), cx + sh_half + 12, waist_y + int(h * 0.12)],
                fill=c_accent,
                width=4,
            )

    @staticmethod
    def _draw_wrapped_text(
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        max_width: int,
        font: Any,
        fill: tuple[int, int, int],
        max_lines: int = 4,
    ) -> None:
        chars_per_line = max(10, max_width // 14)
        lines = [text[i : i + chars_per_line] for i in range(0, len(text), chars_per_line)][:max_lines]
        for idx, line in enumerate(lines):
            draw.text((x, y + idx * 20), line, fill=fill, font=font)
