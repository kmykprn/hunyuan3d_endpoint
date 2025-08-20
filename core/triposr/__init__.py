# TripoSR Package
from .tsr.system import TSR
from .tsr.utils import remove_background, resize_foreground, save_video
from .triposr import main, bg_removal_and_normalize_image, generate_3d_mesh_from_image

__version__ = "1.0.0"
__all__ = [
    "TSR",
    "main",
    "bg_removal_and_normalize_image", 
    "generate_3d_mesh_from_image",
    "remove_background",
    "resize_foreground",
    "save_video",
]