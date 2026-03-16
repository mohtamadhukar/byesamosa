import subprocess
import sys
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Module-level singleton state for the pull subprocess
_lock = threading.Lock()
_process: subprocess.Popen | None = None
_output: str = ""
_status: str = "idle"  # idle | running | completed | failed
_pull_result: str | None = None  # downstream pull result status

# Repo root: routers/ → api/ → byesamosa/ → src/ → repo root
_project_root = Path(__file__).resolve().parent.parent.parent.parent.parent


class PullStatusResponse(BaseModel):
    status: str
    output: str
    pull_result: str | None = None  # "downloaded" | "requested" | "processing" | "request_failed"


def _extract_pull_result(output: str) -> str | None:
    """Extract the pull result status from pipeline output."""
    if "Export downloaded to" in output:
        return "downloaded"
    if "Export has been requested" in output or "try again in ~48 hours" in output:
        return "requested"
    if "is being prepared" in output:
        return "processing"
    if "request may not have gone through" in output:
        return "request_failed"
    return None


def _read_output() -> None:
    """Background thread that reads subprocess stdout to completion."""
    global _output, _status, _process, _pull_result
    if _process is None or _process.stdout is None:
        return
    try:
        for line in _process.stdout:
            _output += line
        _process.wait()
        _status = "completed" if _process.returncode == 0 else "failed"
        _pull_result = _extract_pull_result(_output)
    except Exception as e:
        _output += f"\nError reading output: {e}"
        _status = "failed"
        _pull_result = None


@router.post("/pipeline/pull")
def trigger_pull():
    global _process, _output, _status, _pull_result

    with _lock:
        if _status == "running":
            raise HTTPException(status_code=409, detail="Pull already in progress")

        _output = ""
        _status = "running"
        _pull_result = None
        _process = subprocess.Popen(
            [sys.executable, "-m", "byesamosa.pipeline", "pull"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(_project_root),
        )

    reader = threading.Thread(target=_read_output, daemon=True)
    reader.start()

    return {"status": "running", "output": ""}


@router.get("/pipeline/status")
def pull_status() -> PullStatusResponse:
    return PullStatusResponse(status=_status, output=_output, pull_result=_pull_result)
