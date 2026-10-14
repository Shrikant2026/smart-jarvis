from fastapi import APIRouter
from app.services.comfyui import get_comfyui_status

router = APIRouter(prefix="/comfyui", tags=["ComfyUI"])


@router.get("/status")
def comfyui_status():
    return get_comfyui_status()
