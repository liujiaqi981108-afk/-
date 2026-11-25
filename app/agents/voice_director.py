"""Agent 08: Senior Character Voice & 4-Stem Soundscape Director (VoiceAndSoundDirectorAgent)."""

from __future__ import annotations

import math
import wave
from pathlib import Path

import av
import numpy as np

from app.agents.base import BaseStudioAgent
from app.models.schemas import (
    AssetBible,
    BodyViewAngle,
    CharacterVocalProfile,
    FoleyFrameCue,
    ShotEditorialBlueprint,
    ShotSoundBlueprint,
    ShotSpec,
    StoryStrategyBlueprint,
)

SAMPLE_RATE = 44100


def decode_audio_to_mono_f32(path: Path, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """Decode any audio file (.mp3 / .wav / .aac) to float32 mono array via PyAV."""
    container = av.open(str(path))
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=target_sr)
    chunks: list[np.ndarray] = []
    for frame in container.decode(audio=0):
        for rframe in resampler.resample(frame):
            chunks.append(rframe.to_ndarray()[0].astype(np.float32))
    for rframe in resampler.resample(None):
        chunks.append(rframe.to_ndarray()[0].astype(np.float32))
    container.close()
    if not chunks:
        return np.zeros(256, dtype=np.float32)
    wav = np.concatenate(chunks)
    idx = np.where(np.abs(wav) > 0.008)[0]
    if len(idx) > 10:
        wav = wav[max(0, idx[0] - 350) : min(len(wav), idx[-1] + 1000)]
    return wav


def apply_spatial_reverb_and_occlusion(
    dry: np.ndarray, preset: str, sr: int = SAMPLE_RATE
) -> np.ndarray:
    """Apply wooden-hall early reflections and 180-deg back-view high-frequency roll-off."""
    wet_mix = 0.06 if preset == "close_dry_vo" else 0.18
    out = dry.copy()
    for delay_ms, gain in ((23, 0.34), (47, 0.21), (79, 0.11)):
        d = int(sr * delay_ms / 1000)
        if d < len(out):
            padded = np.zeros_like(out)
            padded[d:] = dry[:-d] * gain
            out = out + padded * wet_mix
    if preset == "off_axis_muffled":
        kernel = np.array([0.25, 0.50, 0.25], dtype=np.float32)
        out = np.convolve(out, kernel, mode="same")
    return out


def mix_into_stereo(
    stereo: np.ndarray,
    mono: np.ndarray,
    start_sec: float,
    gain: float = 1.0,
    pan: float = 0.0,
    sr: int = SAMPLE_RATE,
) -> tuple[int, int]:
    s_idx = max(0, int(round(start_sec * sr)))
    e_idx = min(stereo.shape[1], s_idx + len(mono))
    n = e_idx - s_idx
    if n <= 0:
        return s_idx, s_idx
    l_gain = gain * math.cos((pan + 1.0) * math.pi / 4.0)
    r_gain = gain * math.sin((pan + 1.0) * math.pi / 4.0)
    stereo[0, s_idx:e_idx] += mono[:n] * l_gain
    stereo[1, s_idx:e_idx] += mono[:n] * r_gain
    return s_idx, e_idx


class VoiceAndSoundDirectorAgent(BaseStudioAgent):
    """08 角色声线与四轨声景总监：五维声学基因锁、生理受力气口、空间混响透视、帧同步拟音与四轨混音合成."""

    agent_id = "agent_08_voice"
    agent_name = "08 角色声线与声景总监"

    async def build_vocal_profiles(
        self,
        project_id: str,
        strategy: StoryStrategyBlueprint,
        bible: AssetBible,
    ) -> list[CharacterVocalProfile]:
        await self.emit(
            project_id,
            "BUILDING_ASSETS",
            "正在为全体出场角色建立五维声学基因档案（Vocal DNA）与跨场次锁音参考锚点…",
        )
        profiles: list[CharacterVocalProfile] = []
        for idx, char in enumerate(bible.characters):
            is_hero = char.character_id == "char_hero"
            if is_hero:
                profiles.append(
                    CharacterVocalProfile(
                        character_id=char.character_id,
                        character_name=char.name,
                        voice_anchor_id="vocal_anchor_cold_mezzo_01",
                        resonance_and_timbre=(
                            "清冷克制青年女中音：胸腔共鸣45%稳住底气 + 口腔清晰咬字40% + 15%极淡风霜沙哑气声颗粒感，绝无甜腻播音腔"
                        ),
                        pitch_and_tempo_baseline="基频 195Hz–225Hz · 常态语速 3.6 字/秒（字字留气口）",
                        cadence_habit="句尾干脆冷冽微沉(Falling Intonation)，质问句尾音收束极快不拖泥带水",
                        reference_prompt_spec="6.5秒无混响近讲纯净干声参考音频，锁定跨低语/冷喝情绪声纹一致性",
                    )
                )
            else:
                profiles.append(
                    CharacterVocalProfile(
                        character_id=char.character_id,
                        character_name=char.name,
                        voice_anchor_id=f"vocal_anchor_gravel_baritone_{idx + 1:02d}",
                        resonance_and_timbre=(
                            "市井圆滑中藏阴鸷的中年男低音：厚重胸喉共鸣65% + 烟嗓磨砂颗粒感，笑声带气音但尾音发紧"
                        ),
                        pitch_and_tempo_baseline="基频 110Hz–140Hz · 常态语速 4.1 字/秒（前热络后骤滞）",
                        cadence_habit="客套寒暄句尾微扬拖半拍，杀机暴露时气息骤停",
                        reference_prompt_spec="7.0秒无混响干声声纹锁，保持伪善客套与惊骇失声同源音色",
                    )
                )

        await self.emit(
            project_id,
            "BUILDING_ASSETS",
            f"五维声学基因档案建档完成：已锁定 {len(profiles)} 组角色专属 `voice_anchor_id`。",
            level="success",
        )
        return profiles

    async def build_sound_blueprints(
        self,
        project_id: str,
        shots: list[ShotSpec],
        bible: AssetBible,
        vocal_profiles: list[CharacterVocalProfile],
        strategy: StoryStrategyBlueprint,
    ) -> list[ShotSoundBlueprint]:
        await self.emit(
            project_id,
            "COMPILING_MANIFEST",
            "正在编纂每镜生理受力气口台本、空间混响透视、材质联动帧同步拟音(Foley)与暴风雨前配乐抽空(Music Drop)…",
        )

        vocal_map = {v.character_id: v for v in vocal_profiles}
        char_map = {c.character_id: c for c in bible.characters}
        scene = bible.scenes[0] if bible.scenes else None
        floor_mat = scene.floor_material_and_acoustic if scene else "青石拼老松木地板"
        subtext_by_line = {ln.surface_line: ln for ln in strategy.subtext_dialogue_list}

        hero = char_map.get("char_hero", bible.characters[0])
        ear_acc = hero.accessories[0] if hero.accessories else None
        chekhov_prop = hero.carried_props[0] if hero.carried_props else None

        blueprints: list[ShotSoundBlueprint] = []
        for shot in shots:
            spk_id = shot.speaker_id
            v_prof = vocal_map.get(spk_id) if spk_id else None
            is_back = shot.spatial_blocking.body_view_angle in (BodyViewAngle.BACK, BodyViewAngle.THREE_QUARTER_BACK)
            is_closeup = shot.six_w_one_h.which_shot_size in ("ECU", "CU", "MCU")

            if not shot.narration.strip():
                lip_mode = "breath_foley_only"
                reverb = "wooden_hall_reverb"
                if shot.anticlipping_pose.is_large_action:
                    acting_script = "[sharp_nose_inhale:120ms] … [Frame 32 丹田短促发力吐气闷哼 Effort Exhale，严禁念白]"
                elif shot.beat_phase == "escalation":
                    acting_script = "[屏息凝神 Breath Held 1.4s — 仅保留极轻耳膜心跳低频脉冲]"
                else:
                    acting_script = "[风雪初入微寒鼻息轻吸 Cold Breath Inhale]"
            else:
                sub_spec = subtext_by_line.get(shot.narration)
                pause_ms = sub_spec.silence_before_ms if sub_spec else 380
                if is_back or shot.co_framing.is_multi_character:
                    lip_mode = "off_camera_reaction"
                elif is_closeup:
                    lip_mode = "on_camera_short_sync"
                else:
                    lip_mode = "off_camera_reaction"

                reverb = "off_axis_muffled" if is_back else "wooden_hall_reverb"
                if "，" in shot.narration:
                    p1, p2 = shot.narration.split("，", 1)
                    acting_script = (
                        f"[pre_breath:180ms] {p1}，[subtext_pause:{pause_ms}ms · 视线落点施压] <stress>{p2}</stress>"
                    )
                else:
                    acting_script = f"[pre_breath:{pause_ms}ms] <stress>{shot.narration}</stress>"

            mid_f = shot.mid_beat_frames[0].frame_index if shot.mid_beat_frames else 16
            foley_list: list[FoleyFrameCue] = [
                FoleyFrameCue(
                    frame_index=4,
                    timestamp_sec=round(4 / 24.0, 2),
                    linked_prop_or_surface_id="scene_floor",
                    source_material=floor_mat[:26],
                    sound_description="靴底接触老松木与积水微沉摩擦环境接触音",
                    stereo_pan="C",
                )
            ]

            if chekhov_prop and (
                shot.six_w_one_h.chekhov_prop_featured == chekhov_prop.prop_id
                or shot.anticlipping_pose.is_large_action
            ):
                foley_list.append(
                    FoleyFrameCue(
                        frame_index=mid_f,
                        timestamp_sec=round(mid_f / 24.0, 2),
                        linked_prop_or_surface_id=chekhov_prop.prop_id,
                        source_material=f"{chekhov_prop.name}（紫竹柄+黄铜机括+青霜钢刃）",
                        sound_description=(
                            "高潮细剑破竹鞘高频金属擦鸣 + 劈飞铁镖清脆金铁交击声"
                            if shot.anticlipping_pose.is_large_action
                            else "大拇指顶开黄铜六角暗扣的清脆金属『咔哒』机括声"
                        ),
                        stereo_pan="L->R" if shot.anticlipping_pose.is_large_action else "C",
                    )
                )

            if ear_acc and (shot.beat_phase in ("escalation", "climax", "afterglow")):
                foley_list.append(
                    FoleyFrameCue(
                        frame_index=min(shot.duration_budget.total_frames_24fps - 2, mid_f + 4),
                        timestamp_sec=round((mid_f + 4) / 24.0, 2),
                        linked_prop_or_surface_id=ear_acc.accessory_id,
                        source_material=f"{ear_acc.name}（{ear_acc.material_and_detail[:20]}）",
                        sound_description="随杀气劲风或停身惯性滞后4帧发出的细碎清越银铃余颤声",
                        stereo_pan="R",
                    )
                )

            is_silence_drop = shot.beat_phase == "escalation" and not shot.narration.strip()
            score_note = (
                "【MUSIC DROP 配乐彻底抽空 1.4s】高潮前骤然切断尺八与低频弦乐，仅留风雪底噪与一声银铃急颤拉满窒息感！"
                if is_silence_drop
                else (
                    "太鼓重击瞬态卡第32帧剑锋交击点切入，急促尺八裂音推向峰值"
                    if shot.beat_phase == "climax"
                    else "极克制低频古琴泛音与暗流Sub-Bass脉冲铺垫"
                )
            )

            blueprints.append(
                ShotSoundBlueprint(
                    shot_id=shot.shot_id,
                    speaker_id=spk_id,
                    voice_anchor_id=v_prof.voice_anchor_id if v_prof else None,
                    lip_sync_mode=lip_mode,  # type: ignore[arg-type]
                    spatial_reverb_preset=reverb,  # type: ignore[arg-type]
                    physiological_acting_script=acting_script,
                    foley_cues=foley_list,
                    continuous_room_tone=(
                        "【跨切镜无缝铺底禁止中断】门外6800K呼啸暴风雪低频风压 + 室内黄铜油灯灯芯细微噼啪燃烧声(-28dBFS)"
                    ),
                    score_and_music_drop=score_note,
                    has_music_drop=is_silence_drop,
                )
            )

        drop_count = sum(1 for b in blueprints if b.has_music_drop)
        await self.emit(
            project_id,
            "COMPILING_MANIFEST",
            f"四轨声景台本编纂完成：全部契诃夫道具与配饰材质已绑定精确帧号拟音，已布置 {drop_count} 处高潮前配乐留白抽空(Music Drop)。",
            level="success",
        )
        return blueprints

    async def synthesize_project_soundtrack(
        self,
        project_id: str,
        shots: list[ShotSpec],
        sound_blueprints: list[ShotSoundBlueprint],
        editorial_blueprints: list[ShotEditorialBlueprint],
    ) -> tuple[np.ndarray, list[tuple[float, float, str]], str]:
        """Synthesize character-locked TTS + 4-stem Foley/RoomTone/Music-Drop master stereo track."""
        await self.emit(
            project_id,
            "GENERATING_VIDEOS",
            f"08 声线总监正在通过 [{self.tts.vendor_name}] 合成角色锁音对白、帧同步金属/银铃拟音、跨镜连续风雪底噪与 Music Drop 配乐母带…",
        )
        total_sec = max(2.0, round(sum(s.duration_budget.final_duration_sec for s in shots), 2))
        n_samples = int(round(total_sec * SAMPLE_RATE))
        rng = np.random.default_rng(42)

        # Stem 3: Continuous cross-cut Blizzard / Environmental Room Tone
        white = rng.normal(0.0, 1.0, n_samples).astype(np.float32)
        wind_low = np.convolve(white, np.ones(90, dtype=np.float32) / 90.0, mode="same") * 0.28
        t_all = np.arange(n_samples, dtype=np.float32) / SAMPLE_RATE
        gust_env = 0.55 + 0.45 * np.sin(2 * np.pi * 0.22 * t_all) * np.sin(2 * np.pi * 0.08 * t_all + 0.9)
        ambience = np.vstack([wind_low * gust_env * 0.20, np.roll(wind_low, 580) * gust_env * 0.20])

        # Stem 4: Dark Cello / Guqin Sub-Drone Score with Music Drop & Climax Surge
        score_mono = (
            0.085 * np.sin(2 * np.pi * 73.42 * t_all)
            + 0.048 * np.sin(2 * np.pi * 110.0 * t_all)
            + 0.022 * np.sin(2 * np.pi * 220.0 * t_all * (1.0 + 0.002 * np.sin(2 * np.pi * 3.2 * t_all)))
        ).astype(np.float32)
        score_env = np.ones(n_samples, dtype=np.float32)

        sound_map = {b.shot_id: b for b in sound_blueprints}
        ed_map = {e.shot_id: e for e in editorial_blueprints}

        # Stem 2: Frame-Synced Material Foley
        foley = np.zeros((2, n_samples), dtype=np.float32)

        def _metallic_click(dur: float = 0.14) -> np.ndarray:
            t = np.arange(int(dur * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
            return ((0.6 * np.sin(2 * np.pi * 2850.0 * t) + 0.4 * np.sin(2 * np.pi * 4620.0 * t)) * np.exp(-t * 48.0)).astype(np.float32)

        def _silver_bell(dur: float = 0.95) -> np.ndarray:
            t = np.arange(int(dur * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
            env = np.exp(-t * 3.0) * (0.65 + 0.35 * np.sin(2 * np.pi * 16.0 * t))
            tones = 0.55 * np.sin(2 * np.pi * 3320.0 * t) + 0.30 * np.sin(2 * np.pi * 4980.0 * t)
            return (tones * env * 0.40).astype(np.float32)

        def _sword_and_taiko(dur: float = 0.80) -> np.ndarray:
            t = np.arange(int(dur * SAMPLE_RATE), dtype=np.float32) / SAMPLE_RATE
            taiko = 0.80 * np.sin(2 * np.pi * (95.0 * np.exp(-t * 5.5) + 48.0) * t) * np.exp(-t * 5.0)
            clang = (0.45 * np.sin(2 * np.pi * 2480.0 * t) + 0.35 * np.sin(2 * np.pi * 3910.0 * t)) * np.exp(-t * 9.0)
            return ((taiko + clang) * 0.62).astype(np.float32)

        # Stem 1: Character-Locked Dialogue with Subtext Pauses & J/L-Cut Offsets
        dialogue = np.zeros((2, n_samples), dtype=np.float32)
        vo_windows: list[tuple[int, int]] = []
        timed_subtitles: list[tuple[float, float, str]] = []
        audio_dir = self.store.project_dir(project_id) / "audio"

        cursor_sec = 0.0
        for shot in shots:
            s_dur = shot.duration_budget.final_duration_sec
            s_start = cursor_sec
            s_end = cursor_sec + s_dur
            cursor_sec = s_end

            s_bp = sound_map.get(shot.shot_id)
            e_bp = ed_map.get(shot.shot_id)

            # Score envelope shaping per beat
            i0, i1 = int(s_start * SAMPLE_RATE), min(n_samples, int(s_end * SAMPLE_RATE))
            if s_bp and s_bp.has_music_drop and i1 > i0:
                fade_n = min(int(0.10 * SAMPLE_RATE), (i1 - i0) // 3)
                if fade_n > 0:
                    score_env[i0 : i0 + fade_n] = np.linspace(1.0, 0.0, fade_n)
                score_env[i0 + fade_n : i1] = 0.0
            elif shot.beat_phase == "climax" and i1 > i0:
                score_env[i0:i1] = 1.42

            # Material Foley placement
            if s_bp:
                for cue in s_bp.foley_cues:
                    cue_t = min(total_sec - 0.1, s_start + cue.timestamp_sec)
                    desc = cue.sound_description
                    if "交击" in desc or "破竹鞘" in desc:
                        mix_into_stereo(foley, _sword_and_taiko(), cue_t, gain=0.72, pan=0.15)
                    elif "银铃" in desc:
                        mix_into_stereo(foley, _silver_bell(), cue_t, gain=0.58, pan=0.40)
                    elif "咔哒" in desc or "暗扣" in desc:
                        mix_into_stereo(foley, _metallic_click(), cue_t, gain=0.50, pan=0.05)

            # Dialogue synthesis & J/L-Cut placement
            line = (shot.narration or "").strip()
            if not line:
                continue

            anchor = (s_bp.voice_anchor_id if s_bp and s_bp.voice_anchor_id else "vocal_anchor_cold_mezzo_01")
            reverb_preset = s_bp.spatial_reverb_preset if s_bp else "wooden_hall_reverb"
            offset_sec = e_bp.audio_offset_sec if e_bp else 0.0
            vo_start = max(0.05, s_start + 0.12 + offset_sec)

            pan_val = -0.25 if shot.spatial_blocking.horizontal_zone == "left_third" else (
                0.22 if shot.spatial_blocking.horizontal_zone == "right_third" else 0.0
            )

            # Split comma clauses to inject authentic 360ms psychological subtext pause!
            clauses = [p.strip() for p in line.split("，") if p.strip()]
            clause_cursor = vo_start
            shot_vo_segments: list[np.ndarray] = []

            for c_idx, clause in enumerate(clauses):
                seg_file = audio_dir / f"shot_{shot.shot_id:02d}_part_{c_idx + 1}.mp3"
                await self.tts.synthesize_speech(
                    text=clause,
                    voice_anchor_id=anchor,
                    output_path=seg_file,
                )
                dry_mono = decode_audio_to_mono_f32(seg_file, target_sr=SAMPLE_RATE)
                wet_mono = apply_spatial_reverb_and_occlusion(dry_mono, reverb_preset, sr=SAMPLE_RATE)
                ws, we = mix_into_stereo(dialogue, wet_mono, clause_cursor, gain=0.96, pan=pan_val)
                vo_windows.append((ws, we))
                shot_vo_segments.append(wet_mono)

                seg_dur = (we - ws) / SAMPLE_RATE
                clean_sub = clause.rstrip("。？！；!")[:11]
                timed_subtitles.append((max(s_start, clause_cursor), min(total_sec, clause_cursor + seg_dur + 0.16), clean_sub))
                clause_cursor += seg_dur + 0.36  # Subtext psychological pause

            if shot_vo_segments:
                combined_shot_vo = np.concatenate(shot_vo_segments)
                shot_wav = audio_dir / f"shot_{shot.shot_id:02d}_vo.wav"
                pcm = np.clip(combined_shot_vo * 32767.0, -32768, 32767).astype(np.int16)
                with wave.open(str(shot_wav), "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(pcm.tobytes())
                shot.audio_clip_url = self.store.asset_url(project_id, "audio", shot_wav.name)

        # Fade out score over final 1.0s
        tail_n = min(int(1.0 * SAMPLE_RATE), n_samples // 4)
        if tail_n > 0:
            score_env[-tail_n:] *= np.linspace(1.0, 0.0, tail_n)
        score = np.vstack([score_mono * score_env, score_mono * score_env])

        # 80ms lookahead sidechain ducking (-7.5dB) on score & room tone under dialogue
        duck = np.ones(n_samples, dtype=np.float32)
        lookahead = int(0.08 * SAMPLE_RATE)
        release = int(0.26 * SAMPLE_RATE)
        for ws, we in vo_windows:
            duck[max(0, ws - lookahead) : min(n_samples, we + release)] = 0.42
        duck_smooth = np.convolve(duck, np.ones(1024, dtype=np.float32) / 1024.0, mode="same")

        master = dialogue + foley + (score * duck_smooth) + (ambience * (0.65 + 0.35 * duck_smooth))
        peak = float(np.max(np.abs(master)))
        if peak > 0.89:
            master = master * (0.89 / peak)

        master_wav_path = audio_dir / "master_soundtrack.wav"
        interleaved = np.empty(master.shape[1] * 2, dtype=np.int16)
        pcm_st = np.clip(master * 32767.0, -32768, 32767).astype(np.int16)
        interleaved[0::2] = pcm_st[0]
        interleaved[1::2] = pcm_st[1]
        with wave.open(str(master_wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(interleaved.tobytes())

        soundtrack_url = self.store.asset_url(project_id, "audio", "master_soundtrack.wav")
        await self.emit(
            project_id,
            "GENERATING_VIDEOS",
            f"四轨立体声母带合成完毕 -> `{soundtrack_url}`（含 {len(timed_subtitles)} 条帧对齐安全区字幕事件）。",
            level="success",
        )
        return master, timed_subtitles, soundtrack_url
