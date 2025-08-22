python3 -c "
from huggingface_hub import snapshot_download
path1 = snapshot_download('tencent/Hunyuan3D-2mini', allow_patterns=['hunyuan3d-dit-v2-mini-fast/*'], cache_dir='/runpod-volume/models/')
path2 = snapshot_download('tencent/Hunyuan3D-2', allow_patterns=['hunyuan3d-paint-v2-0-turbo/*'], cache_dir='/runpod-volume/models/')
path3 = snapshot_download('tencent/Hunyuan3D-2', allow_patterns=['hunyuan3d-delight-v2-0/*'], cache_dir='/runpod-volume/models/')
print('Downloaded to:', path1, path2, path3)
"