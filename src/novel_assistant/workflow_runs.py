from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class WorkflowRun(BaseModel):
    workflow_id: str
    project_id: str
    status: Literal["running", "completed", "failed"]
    progress: dict[str, Any]
    request: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class WorkflowRunStore:
    def __init__(self, root: str | Path = "data/workflow-runs") -> None:
        self.root = Path(root)

    def create(
        self,
        workflow_id: str,
        project_id: str,
        request: dict[str, Any],
        progress: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        timestamp = _now()
        run = WorkflowRun(
            workflow_id=workflow_id,
            project_id=project_id,
            status="running",
            progress=progress or _initial_progress(request),
            request=request,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._write(run)
        return run

    def complete(
        self,
        workflow_id: str,
        result: dict[str, Any],
        progress: dict[str, Any],
    ) -> WorkflowRun:
        run = self._require(workflow_id)
        completed = run.model_copy(
            update={
                "status": "completed",
                "progress": progress,
                "result": result,
                "error": None,
                "updated_at": _now(),
            }
        )
        self._write(completed)
        return completed

    def fail(self, workflow_id: str, error: str) -> WorkflowRun:
        run = self._require(workflow_id)
        failed = run.model_copy(
            update={
                "status": "failed",
                "error": error,
                "updated_at": _now(),
            }
        )
        self._write(failed)
        return failed

    def get(self, workflow_id: str) -> WorkflowRun | None:
        path = self._path(workflow_id)
        if not path.exists():
            return None
        return WorkflowRun.model_validate_json(path.read_text(encoding="utf-8"))

    def _require(self, workflow_id: str) -> WorkflowRun:
        run = self.get(workflow_id)
        if run is None:
            raise KeyError(f"Workflow run not found: {workflow_id}")
        return run

    def _write(self, run: WorkflowRun) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(run.workflow_id).write_text(
            json.dumps(run.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _path(self, workflow_id: str) -> Path:
        return self.root / f"{workflow_id}.json"


def _initial_progress(request: dict[str, Any]) -> dict[str, Any]:
    start_chapter = int(request.get("start_chapter") or 1)
    end_chapter = int(request.get("end_chapter") or start_chapter)
    return {
        "total_chapters": int(request.get("chapter_count") or 1),
        "completed_chapters": 0,
        "current_chapter": start_chapter,
        "target_chapters": end_chapter - start_chapter + 1,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()
