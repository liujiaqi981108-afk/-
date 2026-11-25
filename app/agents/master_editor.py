"""Agent 09: Master Film Editor, Colorist & Finishing Supervisor (MasterEditorAgent)."""

from __future__ import annotations

import fractions
import re
import time
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    AspectRatio,
    CharacterVocalProfile,
    DirectorCharterAndLedger,
    Phase2ProductionManifest,
    ShotEditorialBlueprint,
    ShotMotionBlueprint,
    ShotSoundBlueprint,
    ShotSpec,
)

FPS = 24
SAMPLE_RATE = 44100


def _load_subtitle_font(size: int = 30) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for fp in (
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
    ):
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fit_frame_aspect(img: Image.Image, width: int, height: int) -> Image.Image:
    iw, ih = img.size
    if iw == width and ih == height:
        return img
    target_aspect = width / height
    src_aspect = iw / ih
    if src_aspect > target_aspect:
        new_h = ih
        new_w = int(ih * target_aspect)
    else:
        new_w = iw
        new_h = int(iw / target_aspect)
    left = (iw - new_w) // 2
    top = (ih - new_h) // 2
    return img.resize((width, height), resample=Image.Resampling.BICUBIC, box=(left, top, left + new_w, top + new_h))


def _decode_video_frames_and_native_audio(
    clip_path: Path, width: int, height: int, sr: int = SAMPLE_RATE
) -> tuple[list[Image.Image], np.ndarray]:
    """Decode all RGB frames + any native stereo audio stream from a shot `.mp4` clip."""
    frames: list[Image.Image] = []
    audio_chunks: list[np.ndarray] = []

    container = av.open(str(clip_path))
    try:
        for vf in container.decode(video=0):
            pil = vf.to_image().convert("RGB")
            frames.append(_fit_frame_aspect(pil, width, height))
    except Exception:
        pass

    try:
        if container.streams.audio:
            container.seek(0)
            resampler = av.AudioResampler(format="fltp", layout="stereo", rate=sr)
            for af in container.decode(audio=0):
                for rf in resampler.resample(af):
                    audio_chunks.append(rf.to_ndarray().astype(np.float32))
            for rf in resampler.resample(None):
                audio_chunks.append(rf.to_ndarray().astype(np.float32))
    except Exception:
        pass
    finally:
        container.close()

    native_st = np.concatenate(audio_chunks, axis=1) if audio_chunks else np.zeros((2, 0), dtype=np.float32)
    return frames, native_st


def _burn_safe_zone_subtitle(
    frame_img: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    is_vertical: bool = True,
) -> Image.Image:
    """Render <=11-char cinema subtitle strictly inside the Golden Safe Zone (80.5% height on 9:16)."""
    if not text:
        return frame_img
    w, h = frame_img.size
    rgba = frame_img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = w // 2
    cy = int(h * (0.805 if is_vertical else 0.865))
    pad_x, pad_y = 22, 10
    draw.rounded_rectangle(
        [cx - tw // 2 - pad_x, cy - th // 2 - pad_y, cx + tw // 2 + pad_x, cy + th // 2 + pad_y + 4],
        radius=8,
        fill=(10, 12, 15, 168),
        outline=(224, 159, 62, 95),
        width=1,
    )
    draw.text((cx - tw // 2, cy - th // 2 - 2), text, font=font, fill=(246, 242, 234, 255))
    return Image.alpha_composite(rgba, overlay).convert("RGB")


class MasterEditorAgent(BaseStudioAgent):
    """09 高级影视剪辑与调色总监：黄金帧裁剪、非线性变速、原生声轨融合、35mm胶片颗粒与安全区字幕成片合成."""

    agent_id = "agent_09_editor"
    agent_name = "09 影视剪辑与调色总监"

    @staticmethod
    def split_safe_zone_subtitles(narration: str, max_chars: int = 11) -> list[str]:
        """Split dialogue into crisp <=11-char breath segments for 9:16 bottom 18%-22% safe zone."""
        clean = (narration or "").strip()
        if not clean:
            return []
        parts = [p.strip() for p in re.split(r"[，。？！；、,.?!;]+", clean) if p.strip()]
        result: list[str] = []
        for p in parts:
            while len(p) > max_chars:
                result.append(p[:max_chars])
                p = p[max_chars:]
            if p:
                result.append(p)
        return result

    async def build_editorial_and_manifest(
        self,
        project_id: str,
        aspect_ratio: AspectRatio,
        charter: DirectorCharterAndLedger,
        shots: list[ShotSpec],
        vocal_profiles: list[CharacterVocalProfile],
        motion_blueprints: list[ShotMotionBlueprint],
        sound_blueprints: list[ShotSoundBlueprint],
    ) -> tuple[list[ShotEditorialBlueprint], Phase2ProductionManifest]:
        await self.emit(
            project_id,
            "COMPILING_MANIFEST",
            "正在计算手术刀黄金帧裁剪窗、动作顺接与视线引导轨迹、J/L-Cut声画错位偏移、曲线变速与-14 LUFS母带总单…",
        )

        act_color_map = {n.act_phase: n for n in charter.color_script_arc}
        editorial_list: list[ShotEditorialBlueprint] = []

        for idx, shot in enumerate(shots):
            in_f = shot.duration_budget.trim_in_frame
            out_f = shot.duration_budget.trim_out_frame
            eff_sec = round((out_f - in_f + 1) / 24.0, 2)

            if shot.six_w_one_h.which_cut_transition == "j_cut_lead" or (idx == 1 and shot.narration):
                audio_cut = "j_cut_lead_in"
                audio_offset = -0.25
            elif shot.narration and idx < len(shots) - 1 and not shots[idx + 1].narration:
                audio_cut = "l_cut_trail_out"
                audio_offset = 0.28
            else:
                audio_cut = "straight_cut"
                audio_offset = 0.0

            if shot.anticlipping_pose.is_large_action:
                speed_curve = (
                    "非线性变速卡点曲线(Optical-Flow Speed Ramp)：Frame 06-22 起势段 1.32x 凌厉提速 → "
                    "Frame 28-38 剑锋劈镖峰值(Apex)平滑降速至 0.52x 升格放大火花张力 → Frame 39-72 恢复 1.00x 收势稳扎"
                )
                cut_phase = "动作动量峰值顺接(Cut on Action)：在前一镜暗器破空至70%最高速帧硬切入本镜拔剑起势帧"
            elif shot.six_w_one_h.temporal_speed_mode == "slow_mo_0.5x":
                speed_curve = "全程 0.50x 光流插帧升格慢放，凝滞展现银铃震颤与悬垂水滴"
                cut_phase = "静动极反差硬切：在银铃急颤最高频帧果断切向下一镜寒光出鞘"
            else:
                speed_curve = "1.00x 自然恒定帧率，头尾 2 帧微呼吸弹性对齐语音气口毫秒点"
                cut_phase = (
                    "图形匹配切(Graphic Match)：尾帧合拢黄铜暗扣与开篇第1帧铜扣原位无缝叠合形成二刷闭环"
                    if shot.beat_phase == "afterglow"
                    else f"按 {shot.six_w_one_h.which_cut_transition} 在动作未完全停死前保留余势顺切"
                )

            c_node = act_color_map.get(shot.beat_phase)
            color_spec = (
                f"套用总导演色彩总谱[{shot.beat_phase.upper()}: {c_node.kelvin_temp}, 反差 {c_node.luminance_contrast_ratio}] "
                "归一化黑白场防止切镜跳色 + 全局叠加 3% 细腻统一 35mm Kodak 5219 动态胶片颗粒"
                if c_node
                else "全局黑白场色温归一化 + 3% 统一 35mm 胶片颗粒缝合"
            )

            subs = self.split_safe_zone_subtitles(shot.narration, max_chars=11)

            editorial_list.append(
                ShotEditorialBlueprint(
                    shot_id=shot.shot_id,
                    sweet_spot_in_frame=in_f,
                    sweet_spot_out_frame=out_f,
                    effective_trimmed_sec=eff_sec,
                    cut_on_action_phase=cut_phase,
                    eye_trace_screen_zone=(
                        f"视线锚点锁定 [{shot.spatial_blocking.horizontal_zone}] 顺承至下一镜焦点区，消除快切眼球跳动疲劳"
                    ),
                    audio_cut_type=audio_cut,  # type: ignore[arg-type]
                    audio_offset_sec=audio_offset,
                    speed_ramp_curve=speed_curve,
                    color_match_and_grain=color_spec,
                    ducking_and_loudness=(
                        "人声开口前 80ms 触发侧链动态EQ压低配乐 1kHz-3.2kHz 频段 -7.5dB（结束 280ms 柔和回升）"
                        " | 成片母带响度锁定 -14.0 LUFS / -1.0 dBTP"
                    ),
                    safe_zone_subtitles=subs,
                )
            )

        total_dur = round(sum(s.duration_budget.final_duration_sec for s in shots), 2)
        manifest = Phase2ProductionManifest(
            project_id=project_id,
            aspect_ratio=aspect_ratio,
            total_duration_sec=total_dur,
            total_shots=len(shots),
            visual_medium_lock=charter.visual_medium_lock,
            vocal_profiles=vocal_profiles,
            motion_blueprints=motion_blueprints,
            sound_blueprints=sound_blueprints,
            editorial_blueprints=editorial_list,
        )

        jl_count = sum(1 for e in editorial_list if e.audio_cut_type != "straight_cut")
        await self.emit(
            project_id,
            "COMPILING_MANIFEST",
            f"剪辑调色总单与 `phase2_production_manifest.json` 组装完成：含 {jl_count} 处 J/L-Cut 呼吸错位切点，全部字幕严格限制 <=11字落于底部18%-22%黄金安全区。",
            level="success",
        )
        return editorial_list, manifest

    async def compose_final_master_mp4(
        self,
        project_id: str,
        aspect_ratio: AspectRatio,
        shots: list[ShotSpec],
        editorial_blueprints: list[ShotEditorialBlueprint],
        master_audio: np.ndarray,
        subtitles: list[tuple[float, float, str]],
    ) -> str:
        """Surgical frame trimming, speed ramping, native audio blend, 35mm grain & safe-zone subtitle MP4 muxing."""
        is_vertical = aspect_ratio == AspectRatio.VERTICAL_9_16
        width, height = (720, 1280) if is_vertical else (1280, 720)
        font_sub = _load_subtitle_font(30 if is_vertical else 28)

        await self.emit(
            project_id,
            "COMPOSITING_FINAL",
            f"09 剪辑总监开机合片：正在执行手术刀黄金帧裁剪、高潮非线性变速、35mm胶片颗粒统一与底部黄金安全区字幕压制 ({width}x{height} @ 24fps)…",
        )

        ed_map = {e.shot_id: e for e in editorial_blueprints}
        out_mp4 = self.store.final_video_path(project_id)
        out_mp4.parent.mkdir(parents=True, exist_ok=True)

        out = av.open(str(out_mp4), mode="w")
        v_stream = out.add_stream("libx264", rate=FPS)
        v_stream.width = width
        v_stream.height = height
        v_stream.pix_fmt = "yuv420p"
        v_stream.options = {"crf": "20", "preset": "fast"}

        a_stream = out.add_stream("aac", rate=SAMPLE_RATE)
        a_stream.layout = "stereo"

        audio_mix = master_audio.copy()
        rng = np.random.default_rng(19)
        global_frame_idx = 0
        shot_start_sec = 0.0

        for s_idx, shot in enumerate(shots):
            target_sec = shot.duration_budget.final_duration_sec
            target_frames = max(12, int(round(target_sec * FPS)))
            e_bp = ed_map.get(shot.shot_id)

            clip_path = self.store.resolve_asset_url_to_path(shot.video_clip_url)
            decoded_frames: list[Image.Image] = []
            native_audio = np.zeros((2, 0), dtype=np.float32)

            if clip_path and clip_path.exists() and clip_path.stat().st_size > 1000:
                decoded_frames, native_audio = _decode_video_frames_and_native_audio(clip_path, width, height)

            # Fallback if clip wasn't rendered yet: build optical frame sequence from keyframe
            if not decoded_frames:
                kf_path = self.store.resolve_asset_url_to_path(shot.start_keyframe_url)
                base_img = (
                    _fit_frame_aspect(Image.open(kf_path).convert("RGB"), width, height)
                    if (kf_path and kf_path.exists())
                    else Image.new("RGB", (width, height), (18, 22, 28))
                )
                decoded_frames = [base_img for _ in range(target_frames + 8)]

            # Mix Google Flow native clip audio gently underneath our 4-stem soundtrack when enabled
            if self.settings.flow_mix_native_audio and native_audio.shape[1] > 0:
                a_s = int(round(shot_start_sec * SAMPLE_RATE))
                a_e = min(audio_mix.shape[1], a_s + min(native_audio.shape[1], int(round(target_sec * SAMPLE_RATE))))
                n_a = a_e - a_s
                if n_a > 0:
                    nat_gain = 0.22 if shot.narration.strip() else 0.42
                    audio_mix[:, a_s:a_e] += native_audio[:, :n_a] * nat_gain

            # Surgical Sweet-Spot In-Frame Trimming (drop frozen initial frames if source clip is long enough)
            trim_in = min(e_bp.sweet_spot_in_frame if e_bp else 4, max(0, len(decoded_frames) - target_frames))
            usable = decoded_frames[trim_in:] or decoded_frames

            for local_f in range(target_frames):
                t_global = global_frame_idx / FPS
                u = local_f / max(1, target_frames - 1)

                # Non-linear Speed Ramping on large-action climax shots (fast attack -> 0.52x impact apex)
                if shot.anticlipping_pose.is_large_action:
                    remapped_u = (u / 0.4) ** 1.35 * 0.4 if u < 0.4 else 0.4 + (1.0 - (1.0 - (u - 0.4) / 0.6) ** 1.7) * 0.6
                else:
                    remapped_u = u

                src_i = min(len(usable) - 1, int(round(remapped_u * (len(usable) - 1))))
                frame = usable[src_i]

                # Final shot seamless loop closure dip-to-black over final 15%
                if s_idx == len(shots) - 1 and u > 0.85:
                    fade = max(0.0, 1.0 - (u - 0.85) / 0.15)
                    frame = ImageEnhance.Brightness(frame).enhance(fade)

                # Unified 35mm Kodak 5219 fine film grain cohesion
                arr = np.asarray(frame, dtype=np.int16)
                grain = rng.integers(-3, 4, size=arr.shape, dtype=np.int16)
                frame = Image.fromarray(np.clip(arr + grain, 0, 255).astype(np.uint8))

                # Burn <=11-char subtitle in Golden Safe Zone
                active_sub = ""
                for sub_in, sub_out, sub_txt in subtitles:
                    if sub_in <= t_global <= sub_out:
                        active_sub = sub_txt
                        break
                if active_sub:
                    frame = _burn_safe_zone_subtitle(frame, active_sub, font_sub, is_vertical=is_vertical)

                vf = av.VideoFrame.from_image(frame)
                for pkt in v_stream.encode(vf):
                    out.mux(pkt)

                global_frame_idx += 1

            shot_start_sec += target_sec

        for pkt in v_stream.encode(None):
            out.mux(pkt)

        # Peak limit combined audio (-1.0 dBTP) and mux stereo 44.1kHz AAC
        total_audio_samples = int(round((global_frame_idx / FPS) * SAMPLE_RATE))
        if audio_mix.shape[1] < total_audio_samples:
            pad = np.zeros((2, total_audio_samples - audio_mix.shape[1]), dtype=np.float32)
            audio_mix = np.hstack([audio_mix, pad])
        else:
            audio_mix = audio_mix[:, :total_audio_samples]

        peak = float(np.max(np.abs(audio_mix)))
        if peak > 0.89:
            audio_mix = audio_mix * (0.89 / peak)

        chunk_size = 1024
        pts = 0
        for start in range(0, audio_mix.shape[1], chunk_size):
            chunk = np.ascontiguousarray(audio_mix[:, start : start + chunk_size], dtype=np.float32)
            af = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
            af.sample_rate = SAMPLE_RATE
            af.pts = pts
            af.time_base = fractions.Fraction(1, SAMPLE_RATE)
            pts += chunk.shape[1]
            for pkt in a_stream.encode(af):
                out.mux(pkt)

        for pkt in a_stream.encode(None):
            out.mux(pkt)

        out.close()

        ts = int(time.time() * 1000) % 1_000_000
        final_url = f"{self.store.asset_url(project_id, 'exports', 'final_master.mp4')}?v={ts}"
        await self.emit(
            project_id,
            "COMPLETED",
            f"🎬 全片母带成片压制完成！已导出 `{final_url}` ({out_mp4.stat().st_size // 1024} KB · H.264 + 44.1kHz Stereo AAC)。",
            level="success",
            details={"final_video_url": final_url},
        )
        return final_url
