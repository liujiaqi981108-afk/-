"""RESTful & SSE streaming endpoints for the 9-Agent Film Studio Workbench."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.agents.director import DirectorOrchestratorAgent
from app.config import get_settings, update_settings
from app.models.schemas import (
    BodyViewAngle,
    CreateProjectRequest,
    KeyframeStrategy,
    ProjectState,
)
from app.providers.flow_browser import FlowManualInterventionRequiredError, check_flow_cdp_status
from app.storage.project_store import get_project_store

router = APIRouter(prefix="/api", tags=["studio"])

NINE_AGENT_ROSTER = [
    {"id": "agent_01_director", "code": "01", "name": "总导演与制片统筹官", "en": "DirectorOrchestrator"},
    {"id": "agent_02_story", "code": "02", "name": "高级剧作策划总监", "en": "StoryStrategist"},
    {"id": "agent_03_storyboard", "code": "03", "name": "视听分镜与帧级导演", "en": "StoryboardDirector"},
    {"id": "agent_04_art", "code": "04", "name": "角色三视图与场景总监", "en": "ArtDirector"},
    {"id": "agent_05_t2i", "code": "05", "name": "空间调度与防穿模生图师", "en": "StoryboardArtist"},
    {"id": "agent_06_critic", "code": "06", "name": "作画监督视觉质检官", "en": "VisualCritic"},
    {"id": "agent_07_motion", "code": "07", "name": "动态物理运镜总监", "en": "MotionDirector"},
    {"id": "agent_08_voice", "code": "08", "name": "角色声线与声景总监", "en": "VoiceAndSoundDirector"},
    {"id": "agent_09_editor", "code": "09", "name": "影视剪辑与调色总监", "en": "MasterEditor"},
]


class PatchShotRequest(BaseModel):
    narration: Optional[str] = None
    duration_sec: Optional[float] = None
    keyframe_strategy: Optional[KeyframeStrategy] = None
    body_view_angle: Optional[BodyViewAngle] = None


class AssetRerollRequest(BaseModel):
    custom_note: str = ""


class ShotRerollRequest(BaseModel):
    feedback: str = ""
    body_view_angle: Optional[BodyViewAngle] = None
    keyframe_strategy: Optional[KeyframeStrategy] = None


class ShotVideoRerollRequest(BaseModel):
    prompt_override: str = ""
    auto_recompose: bool = True


class FlowEnableRequest(BaseModel):
    cdp_url: Optional[str] = None
    enable_image_nano_banana: bool = True
    enable_video_flow: bool = True


def _orchestrator() -> DirectorOrchestratorAgent:
    return DirectorOrchestratorAgent(store=get_project_store(), settings=get_settings())


@router.get("/health")
async def health_check() -> dict[str, Any]:
    cfg = get_settings()
    return {
        "status": "ok",
        "agents": NINE_AGENT_ROSTER,
        "vendors": {
            "llm": cfg.llm_vendor,
            "image": cfg.image_vendor,
            "video": cfg.video_vendor,
            "tts": cfg.tts_vendor,
        },
    }


@router.get("/flow-browser/status")
async def get_flow_browser_status(cdp_url: Optional[str] = Query(default=None)) -> dict[str, Any]:
    cfg = get_settings()
    target_cdp = (cdp_url or cfg.flow_cdp_url).strip()
    return await check_flow_cdp_status(cdp_url=target_cdp, flow_web_url=cfg.flow_web_url)


@router.post("/flow-browser/enable")
async def enable_local_flow_suite(req: FlowEnableRequest) -> dict[str, Any]:
    patch: dict[str, Any] = {"tts_vendor": "edge_tts"}
    if req.cdp_url:
        patch["flow_cdp_url"] = req.cdp_url.strip()
    if req.enable_image_nano_banana:
        patch["image_vendor"] = "flow_browser"
    if req.enable_video_flow:
        patch["video_vendor"] = "flow_browser"
    cfg = update_settings(patch)
    status = await check_flow_cdp_status(cdp_url=cfg.flow_cdp_url, flow_web_url=cfg.flow_web_url)
    return {"settings": cfg.masked_dict(), "flow_status": status}


@router.get("/settings/providers")
async def read_provider_settings() -> dict[str, Any]:
    return get_settings().masked_dict()


@router.put("/settings/providers")
async def write_provider_settings(patch: dict[str, Any]) -> dict[str, Any]:
    updated = update_settings(patch)
    return updated.masked_dict()


@router.get("/projects")
async def list_all_projects() -> list[dict[str, Any]]:
    return get_project_store().list_projects()


@router.post("/projects")
async def create_and_start_project(
    req: CreateProjectRequest,
    background: bool = Query(default=True),
) -> ProjectState:
    store = get_project_store()
    state = await store.create_project(req)
    orch = _orchestrator()
    if background:
        asyncio.create_task(orch.run_from_start(state.project_id))
        return state
    return await orch.run_from_start(state.project_id)


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> ProjectState:
    try:
        return await get_project_store().load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/approve-script")
async def approve_gate1_script(
    project_id: str,
    background: bool = Query(default=True),
) -> ProjectState:
    store = get_project_store()
    try:
        state = await store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    orch = _orchestrator()
    if background:
        asyncio.create_task(orch.approve_script_and_continue(project_id))
        return state
    return await orch.approve_script_and_continue(project_id)


@router.post("/projects/{project_id}/approve-assets")
async def approve_gate2_assets(
    project_id: str,
    background: bool = Query(default=True),
) -> ProjectState:
    store = get_project_store()
    try:
        state = await store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    orch = _orchestrator()
    if background:
        asyncio.create_task(orch.approve_assets_and_continue(project_id))
        return state
    return await orch.approve_assets_and_continue(project_id)


@router.post("/projects/{project_id}/approve-storyboard")
async def approve_gate3_storyboard(
    project_id: str,
    background: bool = Query(default=True),
) -> ProjectState:
    store = get_project_store()
    try:
        state = await store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    orch = _orchestrator()
    if background:
        asyncio.create_task(orch.approve_storyboard_and_finalize(project_id))
        return state
    return await orch.approve_storyboard_and_finalize(project_id)


@router.post("/projects/{project_id}/run-phase2")
async def start_phase2_video_and_master(
    project_id: str,
    background: bool = Query(default=True),
    skip_existing_clips: bool = Query(default=True),
) -> ProjectState:
    store = get_project_store()
    try:
        state = await store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    orch = _orchestrator()
    if background:
        asyncio.create_task(
            orch.run_phase2_production(project_id, skip_existing_clips=skip_existing_clips)
        )
        return state
    return await orch.run_phase2_production(project_id, skip_existing_clips=skip_existing_clips)


@router.post("/projects/{project_id}/shots/{shot_id}/reroll-video")
async def reroll_shot_video_clip(
    project_id: str, shot_id: int, req: ShotVideoRerollRequest
) -> ProjectState:
    try:
        return await _orchestrator().reroll_single_shot_video(
            project_id=project_id,
            shot_id=shot_id,
            prompt_override=req.prompt_override,
            auto_recompose=req.auto_recompose,
        )
    except FlowManualInterventionRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError, TimeoutError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/shots/{shot_id}/upload-video")
async def upload_shot_video_clip(
    project_id: str,
    shot_id: int,
    file: UploadFile = File(...),
    auto_recompose: bool = Query(default=True),
) -> ProjectState:
    try:
        raw_bytes = await file.read()
        return await _orchestrator().save_uploaded_shot_video(
            project_id=project_id,
            shot_id=shot_id,
            raw_mp4_bytes=raw_bytes,
            auto_recompose=auto_recompose,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/recompose")
async def recompose_project_master_mp4(
    project_id: str,
    background: bool = Query(default=False),
) -> ProjectState:
    store = get_project_store()
    try:
        state = await store.load(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    orch = _orchestrator()
    if background:
        asyncio.create_task(orch.recompose_master_video(project_id))
        return state
    return await orch.recompose_master_video(project_id)


@router.patch("/projects/{project_id}/shots/{shot_id}")
async def patch_shot_script(
    project_id: str, shot_id: int, req: PatchShotRequest
) -> ProjectState:
    try:
        return await _orchestrator().update_shot_script(
            project_id=project_id,
            shot_id=shot_id,
            narration=req.narration,
            duration_sec=req.duration_sec,
            keyframe_strategy=req.keyframe_strategy,
            body_view_angle=req.body_view_angle,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/characters/{character_id}/reroll")
async def reroll_character_turnaround(
    project_id: str, character_id: str, req: AssetRerollRequest
) -> ProjectState:
    try:
        return await _orchestrator().reroll_character_asset(
            project_id=project_id,
            character_id=character_id,
            custom_note=req.custom_note,
        )
    except FlowManualInterventionRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/scenes/{scene_id}/reroll")
async def reroll_scene_plate(
    project_id: str, scene_id: str, req: AssetRerollRequest
) -> ProjectState:
    try:
        return await _orchestrator().reroll_scene_asset(
            project_id=project_id,
            scene_id=scene_id,
            custom_note=req.custom_note,
        )
    except FlowManualInterventionRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/shots/{shot_id}/reroll")
async def reroll_shot_keyframe(
    project_id: str, shot_id: int, req: ShotRerollRequest
) -> ProjectState:
    try:
        return await _orchestrator().reroll_single_shot(
            project_id=project_id,
            shot_id=shot_id,
            feedback=req.feedback,
            body_view_angle=req.body_view_angle,
            keyframe_strategy=req.keyframe_strategy,
        )
    except FlowManualInterventionRequiredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/manifest")
async def download_phase2_manifest(project_id: str) -> FileResponse:
    path = get_project_store().manifest_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Manifest not generated yet")
    return FileResponse(
        path=path,
        media_type="application/json",
        filename=f"{project_id}_phase2_production_manifest.json",
    )


@router.get("/projects/{project_id}/final-video")
async def download_final_master_video(project_id: str) -> FileResponse:
    path = get_project_store().final_video_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Final master video not composed yet")
    return FileResponse(
        path=path,
        media_type="video/mp4",
        filename=f"{project_id}_final_master.mp4",
    )


@router.get("/projects/{project_id}/stream")
async def stream_project_events(project_id: str) -> StreamingResponse:
    store = get_project_store()
    if not store.state_path(project_id).exists():
        raise HTTPException(status_code=404, detail="Project not found")

    async def _event_gen():
        it = store.subscribe(project_id).__aiter__()
        while True:
            try:
                payload = await asyncio.wait_for(it.__anext__(), timeout=15.0)
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
            except StopAsyncIteration:
                break

    return StreamingResponse(
        _event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
