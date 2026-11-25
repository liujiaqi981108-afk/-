"""Async-safe workspace manager, state persistence, and SSE event hub."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import AsyncIterator, Callable, Optional

from app.config import WORKSPACES_DIR
from app.models.schemas import (
    AgentActivityEvent,
    CreateProjectRequest,
    Phase2ProductionManifest,
    ProjectState,
    utc_now_iso,
)


class ProjectStore:
    """Manages project directories, atomic JSON state saves, and SSE subscribers."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir or WORKSPACES_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}
        self._subscribers: dict[str, list[asyncio.Queue[dict]]] = {}

    def _get_lock(self, project_id: str) -> asyncio.Lock:
        if project_id not in self._locks:
            self._locks[project_id] = asyncio.Lock()
        return self._locks[project_id]

    def project_dir(self, project_id: str) -> Path:
        p = self.base_dir / project_id
        p.mkdir(parents=True, exist_ok=True)
        for sub in ("turnarounds", "scenes", "keyframes", "clips", "audio", "exports"):
            (p / sub).mkdir(parents=True, exist_ok=True)
        return p

    def state_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "state.json"

    def manifest_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "exports" / "phase2_production_manifest.json"

    def final_video_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "exports" / "final_master.mp4"

    def asset_url(self, project_id: str, subdir: str, filename: str) -> str:
        return f"/workspaces/{project_id}/{subdir}/{filename}"

    def resolve_asset_url_to_path(self, url: Optional[str]) -> Optional[Path]:
        if not url:
            return None
        clean = url.split("?", 1)[0]
        prefix = "/workspaces/"
        if clean.startswith(prefix):
            rel = clean[len(prefix) :]
            candidate = self.base_dir / rel
            if candidate.exists():
                return candidate
        p = Path(clean)
        return p if p.exists() else None

    async def create_project(self, req: CreateProjectRequest) -> ProjectState:
        project_id = f"proj_{uuid.uuid4().hex[:10]}"
        self.project_dir(project_id)
        state = ProjectState(
            project_id=project_id,
            topic=req.topic.strip(),
            aspect_ratio=req.aspect_ratio,
            target_duration_sec=req.target_duration_sec,
            style_preset=req.style_preset,
            execution_mode=req.execution_mode,
            shot_count_hint=req.shot_count_hint,
        )
        await self.save(state)
        return state

    async def save(self, state: ProjectState) -> ProjectState:
        async with self._get_lock(state.project_id):
            state.updated_at = utc_now_iso()
            target = self.state_path(state.project_id)
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(target)
        await self.broadcast(
            state.project_id,
            {
                "type": "state_sync",
                "stage": state.stage.value,
                "active_agent": state.active_agent,
                "updated_at": state.updated_at,
            },
        )
        return state

    async def mutate(
        self, project_id: str, mutator: Callable[[ProjectState], None]
    ) -> ProjectState:
        async with self._get_lock(project_id):
            state = self.load_sync(project_id)
            mutator(state)
            state.updated_at = utc_now_iso()
            target = self.state_path(project_id)
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(target)
        await self.broadcast(
            project_id,
            {
                "type": "state_sync",
                "stage": state.stage.value,
                "active_agent": state.active_agent,
                "updated_at": state.updated_at,
            },
        )
        return state

    def load_sync(self, project_id: str) -> ProjectState:
        path = self.state_path(project_id)
        if not path.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProjectState(**data)

    async def load(self, project_id: str) -> ProjectState:
        return self.load_sync(project_id)

    def list_projects(self) -> list[dict]:
        items: list[dict] = []
        if not self.base_dir.exists():
            return items
        for child in sorted(self.base_dir.iterdir(), reverse=True):
            sp = child / "state.json"
            if child.is_dir() and sp.exists():
                try:
                    raw = json.loads(sp.read_text(encoding="utf-8"))
                    items.append(
                        {
                            "project_id": raw.get("project_id"),
                            "topic": raw.get("topic"),
                            "title": (raw.get("director_charter") or {}).get("title")
                            or raw.get("topic", "")[:24],
                            "stage": raw.get("stage"),
                            "aspect_ratio": raw.get("aspect_ratio"),
                            "execution_mode": raw.get("execution_mode"),
                            "shot_count": len(raw.get("shots") or []),
                            "final_video_url": raw.get("final_video_url"),
                            "created_at": raw.get("created_at"),
                            "updated_at": raw.get("updated_at"),
                        }
                    )
                except Exception:
                    continue
        items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return items

    async def save_manifest(
        self, project_id: str, manifest: Phase2ProductionManifest
    ) -> str:
        path = self.manifest_path(project_id)
        path.write_text(
            json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.asset_url(project_id, "exports", "phase2_production_manifest.json")

    async def append_event(
        self, project_id: str, event: AgentActivityEvent
    ) -> None:
        async with self._get_lock(project_id):
            state = self.load_sync(project_id)
            state.agent_logs.append(event)
            if len(state.agent_logs) > 250:
                state.agent_logs = state.agent_logs[-250:]
            state.active_agent = event.agent_id
            state.updated_at = utc_now_iso()
            target = self.state_path(project_id)
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(target)
        await self.broadcast(
            project_id,
            {
                "type": "agent_event",
                "event": event.model_dump(mode="json"),
            },
        )

    async def broadcast(self, project_id: str, payload: dict) -> None:
        queues = self._subscribers.get(project_id, [])
        for q in list(queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, project_id: str) -> AsyncIterator[dict]:
        q: asyncio.Queue[dict] = asyncio.Queue(maxsize=200)
        self._subscribers.setdefault(project_id, []).append(q)
        try:
            yield {"type": "connected", "project_id": project_id}
            while True:
                item = await q.get()
                yield item
        finally:
            subs = self._subscribers.get(project_id, [])
            if q in subs:
                subs.remove(q)


_DEFAULT_STORE: Optional[ProjectStore] = None


def get_project_store() -> ProjectStore:
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = ProjectStore()
    return _DEFAULT_STORE


def set_project_store(store: ProjectStore) -> None:
    global _DEFAULT_STORE
    _DEFAULT_STORE = store
