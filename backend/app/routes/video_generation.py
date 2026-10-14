import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.comfyui import (
    get_comfyui_status,
    get_gpu_status,
    get_memory_status,
)
from app.services.video_generation import (
    prepare_video_workflow,
    submit_video_workflow,
    get_video_job,
)

router = APIRouter(prefix="/video", tags=["Video Generation"])


class VideoPreviewRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    scenes: list[dict] = Field(min_length=1, max_length=8)
    test_mode: bool = False


@router.post("/preview")
def preview_video(request: VideoPreviewRequest):
    # Keep API control fields out of the story sent to the model.
    story = request.model_dump(exclude={"test_mode"})

    try:
        workflow = prepare_video_workflow(
            story, test_mode=request.test_mode
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prompt = workflow["405:376"]["inputs"]["value"]
    resolution = workflow.get("409", {}).get("inputs", {})

    return {
        "ready": True,
        "submitted": False,
        "message": "Workflow prepared only. No video job was submitted.",
        "title": request.title,
        "scene_count": len(request.scenes),
        "test_mode": request.test_mode,
        "workflow": "test" if request.test_mode else "standard",
        "aspect_ratio": resolution.get("aspect_ratio"),
        "megapixels": resolution.get("megapixels"),
        "duration_seconds": workflow.get("405:362", {})
            .get("inputs", {}).get("value"),
        "fps": workflow.get("405:361", {})
            .get("inputs", {}).get("value"),
        "prompt_node": "405:376",
        "prompt_characters": len(prompt),
        "save_node": "75",
        "filename_prefix": workflow["75"]["inputs"]["filename_prefix"],
    }


@router.get("/preflight")
def video_preflight(test_mode: bool = True):
    """Inspect readiness without loading models or submitting a job."""
    memory = get_memory_status()
    gpu = get_gpu_status()
    comfyui = get_comfyui_status()

    connected = comfyui.get("connected", False)
    queue_idle = (
        connected
        and comfyui.get("running_jobs") == 0
        and comfyui.get("pending_jobs") == 0
    )

    # Standard generation remains disabled until the short test
    # has been validated on this machine.
    mode_allowed = test_mode

    checks_passed = (
        memory["ram_safe"]
        and gpu.get("gpu_safe", False)
        and queue_idle
        and mode_allowed
    )

    return {
        "ready": checks_passed,
        "generation_started": False,
        "mode": "test" if test_mode else "standard",
        "checks": {
            "memory": memory,
            "gpu": gpu,
            "comfyui_connected": connected,
            "queue_idle": queue_idle,
            "test_mode_required": True,
            "mode_allowed": mode_allowed,
            "torch_memory": comfyui.get("torch_memory", []),
        },
        "message": (
            "Basic safety gates passed. A short test is eligible "
            "for submission; generation has not started."
            if checks_passed
            else "Preflight blocked. Check RAM, GPU free memory, "
                 "ComfyUI connection/queue, and test mode."
        ),
    }


@router.post("/submit")
def submit_video(request: VideoPreviewRequest):
    """Submit only a short test after all safety gates pass."""
    if not request.test_mode:
        raise HTTPException(
            status_code=403,
            detail=(
                "Standard video generation is temporarily disabled. "
                "Use test_mode=true until the short test is validated."
            ),
        )

    preflight = video_preflight(test_mode=True)
    if not preflight["ready"]:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Video generation blocked by safety preflight.",
                "preflight": preflight,
            },
        )

    story = request.model_dump(exclude={"test_mode"})

    try:
        result = submit_video_workflow(story, test_mode=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not communicate with ComfyUI: {exc}",
        ) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "message": "Short test job submitted to ComfyUI.",
        "warning": "GPU and memory usage should be monitored during the test.",
        **result,
    }


@router.get("/status/{prompt_id}")
def video_status(prompt_id: str):
    try:
        return get_video_job(prompt_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not communicate with ComfyUI: {exc}",
        ) from exc
