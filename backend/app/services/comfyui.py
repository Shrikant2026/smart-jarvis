import csv
import os
import subprocess

import psutil
import requests

COMFYUI_URL = os.getenv(
    "COMFYUI_URL", "http://127.0.0.1:8188"
).rstrip("/")
COMFYUI_TIMEOUT = int(os.getenv("COMFYUI_TIMEOUT", "10"))


def get_memory_status() -> dict:
    memory = psutil.virtual_memory()
    available_gib = memory.available / (1024 ** 3)
    minimum_gib = float(
        os.getenv("VIDEO_MIN_AVAILABLE_RAM_GIB", "4.0")
    )

    return {
        "available_ram_gib": round(available_gib, 2),
        "minimum_required_gib": minimum_gib,
        "ram_safe": available_gib >= minimum_gib,
    }


def get_gpu_status() -> dict:
    """Read system-wide GPU memory through NVIDIA's utility."""
    minimum_mib = int(
        os.getenv("VIDEO_MIN_FREE_VRAM_MIB", "3500")
    )

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        rows = list(csv.reader(result.stdout.strip().splitlines()))
        if not rows or len(rows[0]) < 3:
            raise ValueError("Unexpected nvidia-smi output.")

        total, used, free = [int(value.strip()) for value in rows[0][:3]]

        return {
            "available": True,
            "source": "nvidia-smi",
            "total_vram_mib": total,
            "used_vram_mib": used,
            "free_vram_mib": free,
            "minimum_free_vram_mib": minimum_mib,
            "gpu_safe": free >= minimum_mib,
        }
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        IndexError,
    ) as exc:
        return {
            "available": False,
            "gpu_safe": False,
            "error": str(exc),
            "minimum_free_vram_mib": minimum_mib,
        }


def get_comfyui_status() -> dict:
    """Report ComfyUI, queue, and PyTorch memory readings."""
    try:
        system_response = requests.get(
            f"{COMFYUI_URL}/system_stats",
            timeout=COMFYUI_TIMEOUT,
        )
        system_response.raise_for_status()

        queue_response = requests.get(
            f"{COMFYUI_URL}/queue",
            timeout=COMFYUI_TIMEOUT,
        )
        queue_response.raise_for_status()

        system = system_response.json()
        queue = queue_response.json()
        devices = system.get("devices", [])

        torch_memory = []
        for device in devices:
            torch_memory.append({
                "name": device.get("name", "unknown"),
                "vram_total_bytes": device.get("torch_vram_total"),
                "vram_free_bytes": device.get("torch_vram_free"),
            })

        return {
            "connected": True,
            "version": system.get("system", {}).get(
                "comfyui_version"
            ),
            "running_jobs": len(queue.get("queue_running", [])),
            "pending_jobs": len(queue.get("queue_pending", [])),
            "torch_memory": torch_memory,
        }
    except (requests.RequestException, ValueError) as exc:
        return {
            "connected": False,
            "error": str(exc),
            "running_jobs": None,
            "pending_jobs": None,
        }
