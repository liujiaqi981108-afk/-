#!/usr/bin/env python3
"""Command-line batch runner for the 9-Agent Short Video Studio Workflow (Phase 1 + Phase 2)."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.agents.director import DirectorOrchestratorAgent
from app.models.schemas import AspectRatio, CreateProjectRequest, ExecutionMode
from app.storage.project_store import get_project_store


async def _run_cli(args: argparse.Namespace) -> None:
    store = get_project_store()
    req = CreateProjectRequest(
        topic=args.topic,
        aspect_ratio=AspectRatio(args.aspect),
        target_duration_sec=args.duration,
        style_preset=args.style,
        execution_mode=ExecutionMode.AUTO,
        shot_count_hint=args.shots,
    )
    state = await store.create_project(req)
    print(f"[Studio CLI] Created project {state.project_id} — starting 9-Agent Phase 1 pipeline...")
    orch = DirectorOrchestratorAgent(store=store)
    final_state = await orch.run_from_start(state.project_id)

    if args.phase2:
        print(f"[Studio CLI] Starting Phase 2 Video Generation, 4-Stem Soundscape & Master MP4 Muxing...")
        final_state = await orch.run_phase2_production(state.project_id)

    summary = {
        "project_id": final_state.project_id,
        "stage": final_state.stage.value,
        "title": final_state.director_charter.title if final_state.director_charter else "",
        "shots": len(final_state.shots),
        "turnarounds": [
            c.turnaround_image_url for c in (final_state.asset_bible.characters if final_state.asset_bible else [])
        ],
        "scene_plates": [
            s.master_plate_image_url for s in (final_state.asset_bible.scenes if final_state.asset_bible else [])
        ],
        "keyframes": [
            {
                "shot_id": s.shot_id,
                "start": s.start_keyframe_url,
                "end": s.end_keyframe_url,
                "video_clip": s.video_clip_url,
            }
            for s in final_state.shots
        ],
        "manifest_path": str(store.manifest_path(final_state.project_id)),
        "final_video_path": (
            str(store.final_video_path(final_state.project_id)) if final_state.final_video_url else None
        ),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 9-Agent Short Video Studio Workflow")
    parser.add_argument("--topic", required=True, help="Creative short video premise")
    parser.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    parser.add_argument("--duration", type=float, default=16.0)
    parser.add_argument("--style", default="35mm 冷峻电影胶片写实")
    parser.add_argument("--shots", type=int, default=None)
    parser.add_argument(
        "--phase2",
        action="store_true",
        help="Also run Phase 2 video rendering, neural TTS + Foley mixing, and final_master.mp4 muxing",
    )
    args = parser.parse_args()
    asyncio.run(_run_cli(args))


if __name__ == "__main__":
    main()
