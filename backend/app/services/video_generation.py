
import copy
import json
import os
import uuid
from pathlib import Path

import requests

WORKFLOW_DIR = Path(__file__).resolve().parents[2] / "workflows"

WORKFLOW_PATHS = {
    "standard": WORKFLOW_DIR / "ltx2_5_t2v_api.json",
    "test": WORKFLOW_DIR / "ltx2_5_t2v_test.json",
}

PROMPT_NODE_ID = "405:376"
COMFYUI_URL = os.getenv(
    "COMFYUI_URL", "http://127.0.0.1:8188"
).rstrip("/")
COMFYUI_TIMEOUT = int(os.getenv("COMFYUI_TIMEOUT", "10"))


def prepare_video_workflow(
    story: dict,
    test_mode: bool = False,
) -> dict:
    """Prepare an LTX-2.5 workflow without submitting it."""
    if not isinstance(story, dict):
        raise ValueError("Story must be a JSON object.")

    if not story.get("scenes"):
        raise ValueError("Story must contain at least one scene.")

    workflow_name = "test" if test_mode else "standard"
    workflow_path = WORKFLOW_PATHS[workflow_name]

    workflow = json.loads(
        workflow_path.read_text(encoding="utf-8")
    )

    prompt_node = workflow.get(PROMPT_NODE_ID)
    if (
        not prompt_node
        or prompt_node.get("class_type")
        != "PrimitiveStringMultiline"
    ):
        raise ValueError(
            "The expected LTX-2.5 prompt node was not found."
        )

    workflow = copy.deepcopy(workflow)
    workflow[PROMPT_NODE_ID]["inputs"]["value"] = json.dumps(
        story,
        ensure_ascii=False,
        indent=2,
    )

    return workflow


def get_comfyui_queue() -> dict:
    """Return ComfyUI's current running and pending jobs."""
    response = requests.get(
        f"{COMFYUI_URL}/queue",
        timeout=COMFYUI_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def submit_video_workflow(
    story: dict,
    test_mode: bool = False,
) -> dict:
    """Submit one workflow to ComfyUI and return its prompt ID."""
    if not test_mode:
        raise RuntimeError(
            "Standard generation is disabled until the short test "
            "has been validated."
        )

    workflow = prepare_video_workflow(
        story,
        test_mode=True,
    )

    # Refuse to submit if the test workflow has drifted from its
    # deliberately small 2-second, 24-FPS, 0.3-MP configuration.
    duration = workflow.get("405:362", {}).get("inputs", {}).get("value")
    fps = workflow.get("405:361", {}).get("inputs", {}).get("value")
    resolution = workflow.get("409", {}).get("inputs", {})

    if duration != 2 or fps != 24:
        raise ValueError(
            "Test workflow must remain 2 seconds at 24 FPS."
        )
    if (
        resolution.get("aspect_ratio") != "9:16 (Portrait Widescreen)"
        or float(resolution.get("megapixels", 0)) > 0.3
    ):
        raise ValueError(
            "Test workflow resolution exceeds the approved test settings."
        )

    queue = get_comfyui_queue()

    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError(
            "ComfyUI already has queued work. Try again when idle."
        )

    client_id = str(uuid.uuid4())
    response = requests.post(
        f"{COMFYUI_URL}/prompt",
        json={
            "prompt": workflow,
            "client_id": client_id,
        },
        timeout=COMFYUI_TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("prompt_id"):
        raise RuntimeError(
            f"ComfyUI did not return a prompt ID: {result}"
        )

    return {
        "prompt_id": result["prompt_id"],
        "client_id": client_id,
        "submitted": True,
        "node_errors": result.get("node_errors", {}),
    }


def get_video_job(prompt_id: str) -> dict:
    """Get the status and history for a ComfyUI prompt ID."""
    if not prompt_id or any(
        char not in "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for char in prompt_id
    ):
        raise ValueError("Invalid ComfyUI prompt ID.")

    queue = get_comfyui_queue()

    for job in queue.get("queue_running", []):
        if len(job) > 1 and job[1] == prompt_id:
            return {"prompt_id": prompt_id, "status": "running"}

    for job in queue.get("queue_pending", []):
        if len(job) > 1 and job[1] == prompt_id:
            return {"prompt_id": prompt_id, "status": "pending"}

    response = requests.get(
        f"{COMFYUI_URL}/history/{prompt_id}",
        timeout=COMFYUI_TIMEOUT,
    )
    response.raise_for_status()
    history = response.json()
    job = history.get(prompt_id)

    if not job:
        return {"prompt_id": prompt_id, "status": "unknown"}

    status_info = job.get("status", {})
    outputs = job.get("outputs", {})

    return {
        "prompt_id": prompt_id,
        "status": (
            "completed"
            if status_info.get("completed")
            else status_info.get("status_str", "unknown")
        ),
        "outputs": outputs,
    }
